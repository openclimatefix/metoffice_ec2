Extract specific parts of the [UK Met Office's UKV and MOGREPS-UK numerical weather predictions from AWS](https://registry.opendata.aws/uk-met-office/), compress, and save to S3 as Zarr.  Intended to run on AWS EC2.


## Install & test locally


## Configure AWS permissions

Go to the AWS Identity and Access Management (IAM) console, and attach policy `AWSLambdaSQSQueueExecutionRole` to the role for the metoffice-aws-lambda function.


### Create bucket for storing NWPs

Create a bucket called `metoffice-nwp`.


## Configure AWS Simple Queue Service (SQS)

When the Met Office uploads new NWPs to S3, they also send a message to an AWS Simple Notification Service topic.  It is possible to trigger lambda functions directly from SNS notifications.  However, this results in the lambda function sometimes triggering too soon.  This often means the lambda function will take a long time (300 seconds) to download the NetCDF file from S3; and sometimes means the lambda function cannot find the NetCDF file at all.

A solution is to set up a Simple Queue Service, and the the SQS to delay messages a little, to ensure that the NetCDF files are ready and waiting on S3 by the time our lambda function triggers.

Set up SQS as per the [Met Office's instructions](https://github.com/MetOffice/aws-earth-examples/blob/master/examples/2.%20Subscribing%20to%20data.ipynb).

Additionally, set these config options on the queue:

* Delivery Delay = 15 minutes (to allow time for each NetCDF file to replicate across S3)


## Configure EC2 instance




### Configure EC2 instance to trigger every hour