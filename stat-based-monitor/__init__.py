from .utilities import utilities as u

util = u()
#admin email is the one that receives an alert when there is an issue with what's being monitored
util.admin = 'dummy_sender@outlook.com'
util.sender = 'dummy_sender@outlook.com'
#these are scenarios from the scenarios.json file. you can run 1 to many scenarios included in the file
util.scenarios_to_run = ['BlockingQueries','LongRunningQueries']
util.scenario_file_path = './docs/scenarios.json'
#ensure that you have a pre-existing keyvault
util.key_vault_uri = "https://qsmonitoringkv.vault.azure.net"

util.import_library('sys')
util.import_library('azure.functions')
sio = util.import_library('io',['StringIO'])
import azure.functions as func
datetime = util.import_library('datetime')

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        util.logging.info('The timer is past due!')

    util.logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',level=util.logging.DEBUG)


    #get the list of scenarios, if, then and receivers items
    run_list = util.get_scenario()
    util.logging.info('successfully read the list of scenarios')

    #for each scenario run the monitor
    for k,run in run_list.items():
        current_scenario_name = k
        util.logging.info("successfully read the specifics of scenario: %s" %(k))

        recipients = ';'.join([v['email'] for v in run[0]['recipients']])
        environment = run[0]['environment']
        if_query = run[0]['ifQuery']
        then_queries = {v['queryName']:v['query'] for v in run[0]['thenQueries']}

        util.logging.info("successfully got the information necessary to alert on scenario %s" %(k))


        try:
            connection_string = util.get_secret_value(environment)
            conn = util.get_connection(connection_string)
            util.logging.info("connection established")

            cursor = util.get_cursor(conn)
            cursor.execute(if_query)
            count_of_alert_condition_satisfied = cursor.fetchone()[0]
            util.commit_close(conn,cursor)

            if(count_of_alert_condition_satisfied == 0):
                util.logging.info("nothing to alert on")

            else:
                util.logging.info("alert conditions met. attempting to send an email")

                f = sio.StringIO()
                result = {}

                #for each query read the buffer into a dictionary to attach to a mimemultipart
                for k,v in then_queries.items():
                    util.logging.info("running the query for %s" %(k))
                    conn = util.get_connection(connection_string)
                    cursor = util.get_cursor(conn)

                    outputquery = "COPY ({0}) TO STDOUT WITH CSV HEADER".format(v)

                    cursor.copy_expert(outputquery, f)

                    util.commit_close(conn,cursor)

                    f.seek(0)
                    result[k] = f.getvalue()

                #send the alert email
                util.send_mail(recipients,util.sender,"Alert: scenario %s in environment %s" %(current_scenario_name, environment),"Please find attached",result)

        except Exception as e:
            util.logging.error('exception occurred: %s'%(e))

    util.logging.info('Python timer trigger function ran at %s', utc_timestamp)

