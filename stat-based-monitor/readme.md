# Monitor your Azure Database for PostgreSQL with a Python function on TimerTrigger

The `TimerTrigger` makes it incredibly easy to have your functions executed on a schedule. This sample demonstrates a simple use case of calling your PostgreSQL monitoring function every 5 minutes.

## How it works

For a `TimerTrigger` to work, you provide a schedule in the form of a [cron expression](https://en.wikipedia.org/wiki/Cron#CRON_expression)(See the link for full details). A cron expression is a string with 6 separate expressions which represent a given schedule via patterns. The pattern we use to represent every 5 minutes is `0 */5 * * * *`. This, in plain text, means: "When seconds is equal to 0, minutes is divisible by 5, for any hour, day of the month, month, day of the week, or year".

It then reads your scenarios file to get queries to run for each scenario and the environment name that will be used to get your securely stored connection string from Azure Keyvault. If there is an alert condition met, it sends an email with relevant information.

## Scenarios file
Your scenario file should follow a hierarchy mapping to:

ScenarioName|
|--> EnvironmentName
|--> IfQuery
|--> ThenQueries
|--|--> QueryName
|--|--> Query
|--> Recipients
|--|--> Email

|Node|Description|
|---|---|
|EnvironmentName| This will be the name of your keyvault secret that will contain the connection string to this environment|
|IfQuery| Query that helps the detection of an event that you are interested in|
|ThenQueries| 1:many queries that will be attached to your alert email to understand the state of the workload at the time of the detected event|

## Prerequisites

1. Create a keyvault and ensure that the keyvault has the connection strings in secrets that are identical to EnvironmentName values in your scenarios.json file
2. Create a policy that lets the identity of your azure function to 'Get' from your 'Secrets'



## Learn more

<TODO> Documentation