# Why container:

- the webpage needs to use browser with javascript enabled, otherwise elements are not interactable
- so we're limited to things that act as a browser with JS enabled - could use selenium, pupeteer, cypress... 
- unfortunately, sizes of those images are 100s of MBs... Chosing [alpine-chrome](https://github.com/Zenika/alpine-chrome) to built on top of
- potential optimizations:
  - run it on ARM fargate (which is 1/4th cheaper). But that requires changes in how the image is built (needs cross env, quemu?)
  - but the above is not fully necessary - we dont need instant results, so we can use FARGATE_SPOT instances
  - we could get rid of the dependencies (dependency on the `requests` package) and just use std lib `urlib` (image size reduction)
- atm potentially I'll use [EcsRunTask](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_stepfunctions_tasks.EcsRunTask.html), but not sure if that supports spot instances 

# Running:

### Running directly with python:
```bash
HO_PASSWORD=<hyperoptic_password> HO_USERNAME=<hyperoptic_username> python3 fetch-bill/main_fetcher.py
``` 

### Runnigng with docker:
```bash
read -s HO_PASSWORD

docker build -t fetcher .

docker container run -it -eHO_USERNAME=chris.wielgo@gmail.com -eHO_PASSWORD=$HO_PASSWORD --rm fetcher
# or like below with CPU & mem constraints
docker container run -it -m2g --cpus=1 -eHO_USERNAME=chris.wielgo@gmail.com -eHO_PASSWORD=$HO_PASSWORD --rm fetcher   
```

At the moment output is provided to `/tmp/requests.pdf`


# Architecture


aws_fetcher       ->      mail_sender
  bill_fetcher