from .utilities import utilities as u

util = u()
func = util.import_library('azure.functions')
sio = util.import_library('io',['StringIO'])
datetime = util.import_library('datetime')

#admin email is the one that receives an alert when there is an issue with what's being monitored
util.admin = 'dummy_sender@outlook.com'
util.sender = 'dummy_sender@outlook.com'
#ensure that you have a pre-existing keyvault
util.key_vault_uri = "https://yourkeyvault.vault.azure.net"
util.environment_name = 'EnvironmentName'

current_scenario_name = 'qs_significant_changes'
recipients = 'youremail@.com'

def main(mytimer: func.functions.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        util.logging.info('The timer is past due!')

    util.logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',level=util.logging.DEBUG)

    try:
        result = util.detect_significantly_different_queries()

        if(result is None):
            util.logging.info("nothing to alert on")

        else:
            util.logging.info("alert conditions met. attempting to send an email")
            #send the alert email
            result['output'] = open('./docs/output.pdf','rb')
            util.send_mail(recipients,util.sender,"Alert: scenario %s in environment %s" %(current_scenario_name, util.environment_name),"Please find attached",result)
    except Exception as e:
            util.logging.error('exception occurred: %s'%(e))

    util.logging.info('Python timer trigger function ran at %s', utc_timestamp)

