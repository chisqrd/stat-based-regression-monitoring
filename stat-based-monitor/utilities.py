class utilities:

    def __init__(self):
        import string
        import logging as logging

        self.logging = logging
        self.admin = 'dummy_sender@outlook.com'
        self.sender = 'dummy_sender@outlook.com'
        self.scenarios_to_run = ['BlockingQueries']
        self.scenario_file_path = './docs/scenarios.json'
        self.key_vault_uri = 'https://qsmonitoringkv.vault.azure.net'
        self.credentials = None
        self.smtpserver = 'smtp.office365.com'
        self.smtpport = 587
        self.sender_secret_name = 'senderSecret'

    # ################################################
    # Import related functions
    # ################################################

    def import_library(self, library_package, library_names = None):
        if library_names is None:
            try:
                self.logging.info("Importing %s library" % library_package)
                return __import__(library_package)
            except ImportError:
                raise ImportError("You need to install %s library for credential retrieval. e.g. pip install %s" %(library_package, library_package.replace('.','-')))
        else:
            try:
                self.logging.info("Importing %s library from %s" %(' and '.join(library_names),library_package))
                return __import__(name=library_package,fromlist=library_names)
            except ImportError:
                raise ImportError("You need to install the required library(ies) %s. e.g. pip install %s" %(','.join(library_names), library_package.replace('.','-')))


    # ################################################
    # Authorization & Authentication related functions
    # ################################################

    def get_credentials(self):
        try:
            j = self.import_library('json')
            sp= self.import_library('azure.common.credentials',['ServicePrincipalCredentials'])
            #import_library('msrestazure.azure_active_directory','MSIAuthentication')
            #self.import_libraries('msrestazure.azure_active_directory','MSIAuthentication')

            with open('.\secrets\secrets.json','r') as data_file:
                data = j.load(data_file)

            TENANT_ID = data['keyvault']['tenant_id']
            # Your Service Principal App ID
            CLIENT = data['keyvault']['client']
            # Your Service Principal Password
            KEY = data['keyvault']['key']

            credentials = sp.ServicePrincipalCredentials(client_id = CLIENT, secret = KEY, tenant = TENANT_ID)
            # As of this time this article was written (Feburary 2018) a system assigned identity could not be used from a development/local
            # environment while using MSIAuthentication. When it's supported, you may enable below line instead of the above lines
            # credentials = MSIAuthentication()
            return credentials
        except:
            self.credentials = None

    def get_secret_value(self,secret_name):
        #secret_name maps to the EnvironmentName in scenarios.json
        kvc = self.import_library('azure.keyvault',['KeyVaultClient'])
        self.import_library('azure.keyvault',['KeyVaultAuthentication'])

        if(self.credentials is None):
            self.credentials = self.get_credentials() 
        key_vault_client = kvc.KeyVaultClient(self.credentials)

        # Your KeyVault URL, name of your secret, the version of the secret. Empty string for latest. Your provided enviroment needs to match the secret name
        return key_vault_client.get_secret(self.key_vault_uri, secret_name,"").value

    # ################################################
    # Sql connectivity related functions
    # ################################################

    def get_connection(self,conn_string):
        psycopg2 = self.import_library('psycopg2')
        try:
            return psycopg2.connect(conn_string)
        except Exception as e:
            self.logging.error("could not establish connection: %s" %(e))

    def get_cursor(self,conn):
        cursor = conn.cursor()
        return cursor

    def commit_close(self,conn,cursor):

        # Cleanup
        conn.commit()
        cursor.close()
        conn.close()

    def rollback_close(self,conn,cursor):

        # Cleanup
        conn.rollback()
        cursor.close()
        conn.close()


    # ################################################
    # Alerting scenario related functions
    # ################################################

    def get_scenario(self,scenario=None):
        os = self.import_library('os')
        json = self.import_library('json')
        try:
    #        if len(sys.argv) == 3:
    #            scenario = sys.argv[1]
    #            scenarioFilePath = sys.argv[2]
    #        else:
    #            raise ValueError("You must set the scenario name and the scenario master file path in order to run this script")
            self.logging.info("Current working directory is: %s" %os.getcwd())
            self.logging.info("Reading the scenario specifics")
            
            with open(self.scenario_file_path,'r') as data_file:
                data = json.load(data_file)

            #read the json entry matching the scenario into a list
            if(scenario is None):
                return data
            else:
                return [v[0] for k,v in data.items() if k == '%s'%(scenario)]

        except ValueError as e:
            self.logging.error("Required arguments not passed: %s" %(e))
            #self.sendMail(ADMIN,SENDER,"Cron job missing arguments","Please review your cron job for missing arguments. Expecting scenario ....py scenarioFilePath in order")

        except Exception as e:
            self.logging.error("Error reading scenario file: %s" %(e))
            #self.sendMail(ADMIN,SENDER,"Cron job cannot start %s scenario" %(scenario),"There is an issue with loading the json section for this scenario. Please ensure json is well-formed.")



    # ################################################
    # Email related functions
    # ################################################

    def send_mail(self,to, fr, subject, text, files={},server='smtp.office365.com'):
        slib = self.import_library('smtplib')
        mmm = self.import_library('email.mime.multipart',['MIMEMultipart'])
        mmb = self.import_library('email.mime.base',['MIMEBase'])
        mmt = self.import_library('email.mime.text',['MIMEText'])
        fd = self.import_library('email.utils',['formatdate'])
        enc = self.import_library('email',['encoders'])

        try:
            msg = mmm.MIMEMultipart()
            msg['From'] = fr
            msg['To'] = to
            msg['Date'] = fd.formatdate(localtime=True)
            msg['Subject'] = subject
            msg.attach( mmt.MIMEText(text) )

            for filekey,filevalue in files.items():
                part = mmb.MIMEBase('application', "octet-stream")
                part.set_payload(filevalue)
                enc.encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"'% filekey)
                msg.attach(part)

            smtp = slib.SMTP(self.smtpserver,self.smtpport)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self.sender,self.get_secret_value(self.sender_secret_name))
            smtp.sendmail(fr, to, msg.as_string() )
            smtp.close()
            self.logging.info("Successfully sent email")

        except slib.SMTPException as e:
            self.logging.error("Unable to send email: %s" %(e))
