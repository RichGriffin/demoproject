# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from absl import app
from absl import flags
import google.oauth2.credentials
from google.oauth2 import service_account
from google.cloud import bigquery_datatransfer_v1
import google.protobuf.json_format
import os

FLAGS = flags.FLAGS

flags.DEFINE_string('table', '', 'Table name for scheduled query output')
flags.DEFINE_string('query_file', '', 'Query to schedule')
flags.DEFINE_string('access_token', '', 'Access token from `gcloud auth print-access-token`')

PROJECT_ID = "four-metrics"
# query_file = "/users/gripp/repos/fourkeys/queries/deployments.sql"
# table = "deployments"
# access_token = 
def get_bq_client():
    # If the BigQuery DataTransfer API has been enabled recently, there is sometimes a delay.
    # Script will retry until the API settings have propagated
    retry = True
    while retry is True:
        try:
            # Set up the client
            # credentials, project = google.auth.default()
            credentials = service_account.Credentials.from_service_account_file('/users/gripp/repos/fourkeys/queries/token.json')
            # authclient = datastore.Client()
            # authclient = Client.from_service_account_json('/path/to/keyfile.json')

            # credentials = google.oauth2.credentials.Credentials(
            #     client_id="764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com",
            #     client_secret="d-FL95Q19q7MQmFpd7hHD0Ty",
            #     quota_project_id="four-metrics",
            # )
            client = bigquery_datatransfer_v1.DataTransferServiceClient(credentials=credentials)
            parent = client.project_path(PROJECT_ID)
            retry = False
        except Exception as e:
            # Only retry for the service account error
            if "BigQuery Data Transfer service account is not found" not in str(e):
                retry = False

    return client, parent


def create_or_update_scheduled_query(argv):
    # Set up the client
    client, parent = get_bq_client()

    # Flags from command line
    table = FLAGS.table
    query_file = FLAGS.query_file

    # Read the query in from the file
    query = open(query_file, "r").read()

    # Create Transfer Config with new params
    transfer_config = google.protobuf.json_format.ParseDict(
        {
            "destination_dataset_id": "four_keys",
            "display_name": table,
            "data_source_id": "scheduled_query",
            "params": {
                "query": query,
                "destination_table_name_template": table,
                "write_disposition": "WRITE_TRUNCATE",
            },
            "schedule": "every 24 hours",
        },
        bigquery_datatransfer_v1.types.TransferConfig(),
    )

    # Update transfer_config if it already exists
    for scheduled_query in client.list_transfer_configs(parent):
        if scheduled_query.display_name == table:

            # Update transfer_config to map to current scheduled_query
            transfer_config.name = scheduled_query.name

            # Set update mask. We only want to update params.
            update_mask = {"paths": ["params"]}

            response = client.update_transfer_config(transfer_config, update_mask)

            # Manually Run the transfer before the next scheduled time
            run_time = google.protobuf.timestamp_pb2.Timestamp()
            run_time.GetCurrentTime()
            client.start_manual_transfer_runs(transfer_config.name, requested_run_time=run_time)
            return f"Updated scheduled query '{response.name}'"

    # Create the transfer config if it doesn't exist
    response = client.create_transfer_config(parent, transfer_config)
    return f"Created scheduled query '{response.name}'"


if __name__ == '__main__':
    app.run(create_or_update_scheduled_query)
