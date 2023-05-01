import functions_framework
from google.cloud import dataform_v1beta1
from pydantic import BaseModel, ValidationError
from typing import List, Optional
import base64
import json


class Config(BaseModel):
    project_id: str
    region: str
    repository_id: str
    git_commitish: str
    tags: Optional[List[str]]
    dataset_id: Optional[str]
    last_event_table: Optional[str]


@functions_framework.cloud_event
def main(cloud_event):
    data = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    message = json.loads(data)
    try:
        config = Config(**message)
    except ValidationError as e:
        print("ValidationError", e)
        return

    compilation_result = {
        "git_commitish": config.git_commitish,
    }

    if config.last_event_table:
        compilation_result["code_compilation_config"] = {
            "vars": {
                    f"GA4_TABLE": config.last_event_table
                }
        }

    parent = f"projects/{config.project_id}/locations/{config.region}/repositories/{config.repository_id}"
    
    try:
        client = dataform_v1beta1.DataformClient()
        result = client.create_compilation_result(
            request={
                "parent": parent,
                "compilation_result": compilation_result,
            }
        )
    except Exception as e:
        print(str(e))

    workflow_invocation = {"compilation_result": result.name}
    if config.tags:
        workflow_invocation["invocation_config"] = {"included_tags": config.tags}

    workflow_invocation_request={"parent": parent, "workflow_invocation": workflow_invocation}

    workflow_invocation_result = client.create_workflow_invocation(
        request=workflow_invocation_request,
    )
    