# Schedule Dataform updates using Cloud Functions

The repository with Cloud Functions for the blog post on [gtm-gear.com](https://gtm-gear.com/posts/dataform-cloud-functions/)


## Preparatory stage
### Activate configuration
```sh
gcloud config configurations list
gcloud config configurations activate [project]
```
### Set variables
```sh
export project_id=$(gcloud info --format='value(config.project)')
export region=us-central1
export repository_id=dataform-ga4events
export git_commitish=main
export dataset=ga4_obfuscated_sample_ecommerce
```

## Create Pub / Sub topics
### Set variables with topic names
```sh
export ga4_table_updated_topic=ga4-table-updated-topic
export dataform_run_topic=dataform-run-topic
```

### Create topics
```sh
gcloud pubsub topics create ${ga4_table_updated_topic}
gcloud pubsub topics create ${dataform_run_topic}
```

## Create sinks

### Set variables for the sink filter
```sh
export sink_filter="protoPayload.methodName=\"jobservice.jobcompleted\" protoPayload.authenticationInfo.principalEmail=\"firebase-measurement@system.gserviceaccount.com\"
protoPayload.serviceData.jobCompletedEvent.job.jobConfiguration.load.destinationTable.datasetId=\"${dataset}\"
protoPayload.serviceData.jobCompletedEvent.job.jobConfiguration.load.destinationTable.tableId=~\"^events_\d+\""
```

### Create the logging sink
```sh
gcloud logging sinks create ga4-table-updated-sink pubsub.googleapis.com/projects/${project_id}/topics/${ga4_table_updated_topic} --log-filter="${sink_filter}"
```

## Grant the sink a Pub/Sub Publisher role on the topic

### Set variable with the sink writerIdentity 
```sh
export sink_writer_identity=$(gcloud logging sinks describe --format='value(writerIdentity)' ga4-table-updated-sink)
```

## Add the sink a Pub/Sub Publisher role
```sh
gcloud pubsub topics add-iam-policy-binding ${ga4_table_updated_topic} --member="${sink_writer_identity}" --role="roles/pubsub.publisher"
```

## Cloud function for sink events


### Deploy ga4-table-updated-pubsub-event-func function
   ```sh
   gcloud functions deploy ga4-table-updated-pubsub-event-func --max-instances 1 --entry-point main --runtime python39 --trigger-resource ${ga4_table_updated_topic} --trigger-event google.pubsub.topic.publish --region ${region} --timeout 540s --set-env-vars project_id=${project_id},region=${region},repository_id=${repository_id},git_commitish=${git_commitish},topic_id=${dataform_run_topic}
   ```

### Set variable with the function service account 
```sh
export function_service_account=$(gcloud functions describe --format='value(serviceAccountEmail)' ga4-table-updated-pubsub-event-func)
```

### Add the Cloud Function's service account Pub/Sub Publisher role
```sh
gcloud pubsub topics add-iam-policy-binding ${dataform_run_topic} --member="serviceAccount:${function_service_account}" --role="roles/pubsub.publisher"
```

## Cloud function for Dataform Run

### Deploy ga4-table-updated-dataform-run-func function
   ```sh
   gcloud functions deploy ga4-table-updated-dataform-run-func --max-instances 1 --entry-point main --runtime python39 --trigger-resource ${dataform_run_topic} --trigger-event google.pubsub.topic.publish --region ${region} --timeout 540s
   ```

## Hourly intraday models update

### Set variable with a message
```sh
export message_body="{\"project_id\":\"${project_id}\",\"region\":\"${region}\",\"repository_id\":\"${repository_id}\",\"git_commitish\":\"${git_commitish}\",\"tags\":[\"ga4_hourly\"]}"
```

### Create a scheduler pubsub job 
```sh
gcloud scheduler jobs create pubsub ga4-hourly --location ${region} --schedule "0 * * * *" --topic ${dataform_run_topic} --message-body ${message_body}
```