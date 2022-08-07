# Why container:

- the webpage needs to use browser with javascript enabled, otherwise elements are not interactable
- so we're limited to things that act as a browser with JS enabled - could use selenium, pupeteer, cypress... 
- unfortunately, sizes of those images are 100s of MBs... Chosing [alpine-chrome](https://github.com/Zenika/alpine-chrome) to built on top of
- potential optimizations:
  - run it on ARM fargate (which is 1/4th cheaper). But that requires changes in how the image is built (needs cross env, quemu?)
  - but the above is not fully necessary - we dont need instant results, so we can use FARGATE_SPOT instances
  - we could get rid of the dependencies (dependency on the `requests` package) and just use std lib `urlib` (image size reduction)
- atm potentially I'll use [EcsRunTask](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_stepfunctions_tasks.EcsRunTask.html), but not sure if that supports spot instances 

# Secrets

I store secrets in the SSM Parameters (SecureString). They are cheaper (free?) than the SecretsManager.
However, they cannot be created in CDK - one needs to do it upfront in [AWS Systems Manager/Parameter Store](https://eu-west-2.console.aws.amazon.com/systems-manager/parameters).
either via Console or CLI:

```shell
ws ssm put-parameter --name "/bill-fetcher/secrets/username"  --type "SecureString" --value "${USERNAME}"
ws ssm put-parameter --name "/bill-fetcher/secrets/password"  --type "SecureString" --value "${PASSWORD}"
```

Outcome should be something like this:

| Name                             | Tier      | Type                               | Last modified |
|----------------------------------|-----------|------------------------------------| --- |
| /bill-fetcher/secrets/password   | Standard  | SecureString	                      | Sat, 06 Aug 2022 13:30:50 GMT |
| /bill-fetcher/secrets/username	  | Standard  | SecureString	                      | Sat, 06 Aug 2022 13:34:37 GMT |

# Verifying email recipient for lambda

This needs to be done as my AWS account is in the Sandbox Environment (haven't sent email limit increase request).
is in early stages and not fully verified.

1) Send verification request to $RECIPIENT_EMAIL_ADDRESS
```shell
aws ses verify-email-identity --email-address $RECIPIENT_EMAIL_ADDRESS
```
2) Check it's on the identities list:
```shell
aws ses list-identities --identity-type EmailAddress
```
3) Open email inbox for RECIPIENT_EMAIL_ADDRESS and click on the verification link
4) Validate status:

```shell
$ aws ses get-identity-verification-attributes --identities $RECIPIENT_EMAIL_ADDRESS | \
    jq '.VerificationAttributes["chriswielgo+ses@gmail.com"].VerificationStatus'
```
Expected output should result in `"Success"`
```


# Running:

### Running directly with python:
```bash
HO_PASSWORD=<hyperoptic_password> HO_USERNAME=<hyperoptic_username> python3 fetch-bill/main_fetcher.py
``` 

### Running with docker:
```bash
read -s HO_PASSWORD

docker build -t fetcher .

docker container run -it -eHO_USERNAME=chris.wielgo@gmail.com -eHO_PASSWORD=$HO_PASSWORD --rm fetcher
# or like below with CPU & mem constraints
docker container run -it -m2g --cpus=1 -eHO_USERNAME=chris.wielgo@gmail.com -eHO_PASSWORD=$HO_PASSWORD --rm fetcher   
```

At the moment output is provided to `/tmp/requests.pdf`

### Testing lambda

```
cdk synth
# check ./cdk.out/BillFetcherStack.template.json for a lambda identifier - e.g. 'billsender283F6E25'
sam local invoke -t ./cdk.out/BillFetcherStack.template.json --event ../src/bill-sender/event.json billsender283F6E25
```

### Configuring PyCharm
#### Configure subprojects
We have one repo and multiple (2) python subprojects, each using `pipenv`. Follow instructions [here](https://youtrack.jetbrains.com/issue/PY-46314/Multiple-Virtual-Environments-via-pipenv-Pipfile-per-project#focus=Comments-27-5550866.0-0) to property configure PyCharm project with attached subprojects.
#### Configure Debugging of lambda with AWS Toolkit
Seems like atm it only works, if was configured with SAM teamplate.yml, not from CDK.
