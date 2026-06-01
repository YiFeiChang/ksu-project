import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

token = os.environ.get("INFLUXDB_TOKEN")
org = "ksu_project"
url = "http://10.0.0.254:8503"

write_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)


bucket="chrono_data"

write_api = write_client.write_api(write_options=SYNCHRONOUS)
   
for value in range(5):
  point = (
    Point("measurement1")
    .tag("tagname1", "tagvalue1")
    .field("field1", value)
  )
  write_api.write(bucket=bucket, org="ksu_project", record=point)
  time.sleep(1) # separate points by 1 second