import functions_framework
from google.cloud import pubsub_v1
import base64, json, os

config = {
    "project_id": os.environ.get("project_id"),
    "region": os.environ.get("region"),
    "repository_id": os.environ.get("repository_id"),
    "git_commitish": os.environ.get("git_commitish"),
    "tags":[]
}

@functions_framework.cloud_event
def main(cloud_event):
    data_buffer = base64.b64decode(cloud_event.data["message"]["data"])
    log_entry = json.loads(data_buffer)

    config["last_event_table"] = log_entry["protoPayload"]["serviceData"]["jobCompletedEvent"]["job"]["jobConfiguration"]["load"]["destinationTable"]["tableId"]
    config["dataset_id"] = log_entry["protoPayload"]["serviceData"]["jobCompletedEvent"]["job"]["jobConfiguration"]["load"]["destinationTable"]["datasetId"]
    config["tags"] = [config["dataset_id"]]

    client = pubsub_v1.PublisherClient()

    topic_id = os.environ.get("topic_id")
    topic_path = client.topic_path(config["project_id"], topic_id)

    response = client.publish(topic_path, json.dumps(config).encode("utf-8"))