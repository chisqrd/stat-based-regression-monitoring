# Monitor your Azure Database for PostgreSQL and detect significant regressions with Python

The `TimerTrigger` makes it incredibly easy to have multiple scenario multiple environment monitoring and alerting executed on a schedule. This sample demonstrates a simple use case of calling your PostgreSQL monitoring function every 5 minutes with two scenarios against two different databases.

## How it works

For a `TimerTrigger` to work, you provide a schedule in the form of a [cron expression](https://en.wikipedia.org/wiki/Cron#CRON_expression)(See the link for full details). A cron expression is a string with 6 separate expressions which represent a given schedule via patterns. The pattern we use to represent every 5 minutes is `0 */5 * * * *`. This, in plain text, means: "When seconds is equal to 0, minutes is divisible by 5, for any hour, day of the month, month, day of the week, or year".

You will need to provide a baseline period and the current period that you want to detect anomalies in. Once you determine your directional preference, p value and change percentage threshold, taking advantage of some of the widely used stats and math libraries, your function will be able to detect the queries that will need your attention and alert you near real time.

## Getting started
### Prerequisites
* [Install Visual Studio Code](https://code.visualstudio.com/Download)
* [Install Docker](https://www.docker.com/get-started)

### Create an app principal

Go to Azure Active Directory and [create an app principal](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-v1-add-azure-ad-app) for your app. You will then need to update your `./secrets/secrets.json` file with your tenant id, principal id and secret.

### Get your KeyVault ready

1. Create a keyvault and ensure that the keyvault has the connection strings in secrets that are identical to `EnvironmentName`. The value for your secret should look like `host=yourservername.postgres.database.azure.com port=5432 dbname=yourdatabase user=dbuser@yourservername password=yourpassword`  
2. In the keyvault, create a policy that lets the app principal you created to `Get` from your `Secrets`
3. Also in the keyvault, create a secret with name that matches to the value of `sender_secret_name variable`. The current value is `senderSecret`

### Update code as needed
There are certain settings that you need to update for your setup. Please ensure that you set below:
#### init.py
`util.admin = 'dummy_sender@outlook.com'`: account that would get emails in case of any issues with your alerting mechanism  
`util.sender = 'dummy_sender@outlook.com'`: account that your alerts will be send from   
`util.key_vault_uri = "https://yourazurekeyvault.vault.azure.net"` : keyvault uri that contains your connection strings by `EnvironmentName` and your sender account secret  
`util.environment_name = 'YourEnvironmentName' : keyvault secret name that contains your connection string to your pg instance

#### secrets.json
At this time, MSIAuthentication is not supported from a local/dev environment as well as Linux based functions and app service plans. To get around this, you will need to create an app principal and provide the required parameters in `secrets\secrets.json`

### Good to go!
You are now ready to deploy. Go to Azure tab in Visual Studio Code, click Deploy and follow instructions.

## Troubleshooting
If you experience below issue while publishing your function to Azure with Visual Studio Code, please follow the instructions [here](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python#publishing-to-azure)

After installing Docker on your dev environment and ensure that it is running, you can run `func azure functionapp publish <app name> --build-native-deps --no-bundles` as instructed from within Visual Studio Code's terminal ![package your app and publish](https://github.com/chisqrd/multi-scenario-env-alerting/blob/master/images/function_docker_deploying.png)

Once upload and deployment completes successfully, you can visit your function in the portal and verify if it is running as expected or if there are some corrective actions you need to take.

![your app published](https://github.com/chisqrd/multi-scenario-env-alerting/blob/master/images/function_deployed.png)

## Learn more
[Taking a closer look at Python support for Azure Functions](https://azure.microsoft.com/en-us/blog/taking-a-closer-look-at-python-support-for-azure-functions/)  
[Functions Reference - Python](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python)