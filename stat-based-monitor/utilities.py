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
        self.environment_name = 'kidb'

    # ################################################
    # Import related functions
    # ################################################

    def import_library(self, library_package, library_names = None):
        try:
            if library_names is None:
                self.logging.info("Importing %s library" % library_package)
                return __import__(library_package)
            else:
                self.logging.info("Importing %s library from %s" %(' and '.join(library_names),library_package))
                return __import__(name=library_package,fromlist=library_names)
        except ImportError:
            raise ImportError('Library was not found: %s' %(library_package))

    # ################################################
    # Authorization & Authentication related functions
    # ################################################

    def get_credentials(self):
        try:
            j = self.import_library('json')
            sp= self.import_library('azure.common.credentials',['ServicePrincipalCredentials'])
            #import_library('msrestazure.azure_active_directory','MSIAuthentication')
            #self.import_libraries('msrestazure.azure_active_directory','MSIAuthentication')

            with open('./secrets/secrets.json','r') as data_file:
                data = j.load(data_file)

            tenant_id = data['keyvault']['tenant_id']
            # Your Service Principal App ID
            client = data['keyvault']['client']
            # Your Service Principal Password
            key = data['keyvault']['key']

            credentials = sp.ServicePrincipalCredentials(client_id = client, secret = key, tenant = tenant_id)
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
        conn.commit()
        cursor.close()
        conn.close()

    def rollback_close(self,conn,cursor):
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
            self.logging.info("Current working directory is: %s" %os.getcwd())
            self.logging.info("Reading the scenario specifics")
            
            with open(self.scenario_file_path,'r') as data_file:
                data = json.load(data_file)

            #read the json entry matching the scenario into a list
            if(scenario is None):
                return data
            else:
                return [v[0] for k,v in data.items() if k == '%s'%(scenario)]

        except Exception as e:
            self.logging.error("Error reading scenario file: %s" %(e))



    # ################################################
    # Email related functions
    # ################################################

    def send_mail(self,to, fr, subject, text, files={},server='smtp.office365.com'):
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.text import MIMEText
        from email.utils import formatdate 
        from email import encoders

        try:
            msg = MIMEMultipart()
            msg['From'] = fr
            msg['To'] = to
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = subject
            msg.attach( MIMEText(text) )

            for filekey,filevalue in files.items():
                part = MIMEBase('application', "pdf")
                part.set_payload(filevalue.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"'% filekey)
                msg.attach(part)

            smtp = smtplib.SMTP(self.smtpserver,self.smtpport)
            smtp.ehlo()
            smtp.starttls()
            smtp.login(self.sender,self.get_secret_value(self.sender_secret_name))
            smtp.sendmail(fr, to, msg.as_string() )
            smtp.close()
            self.logging.info("Successfully sent email")

        except smtplib.SMTPException as e:
            self.logging.error("Unable to send email: %s" %(e))

    def detect_significantly_different_queries(
         self, 
         aggregation_function = 'sum',         
         column_to_evaluate = 'mean_time',
         baseline_period_start = '2018-08-01 10:00:00-07',
         baseline_period_end = '2019-02-15 10:00:00-07',
         current_period_start = '2019-02-15 10:00:00-07',
         current_period_end = '2019-03-01 10:00:00-07',
         p_threshold = 0.05,
         directional_preference = 1, # -1 for decrease, +1 for increase, 0 for either way
         percent_change_threshold = 0.05
        ):

        import pandas as pd
        import numpy as np
        from scipy.stats import ttest_ind, ttest_ind_from_stats
        #from scipy.special import stdtr
        import matplotlib.backends.backend_pdf
        import matplotlib.pyplot as plt
        pdfs = {}

        qs_metric_aggregation_grouped_by = "with ordered_qs_aggregation as (\
            select query_id as group_by, query_sql_text, start_time, datname, %s(%s) as metric \
            from query_store.qs_view join pg_database on query_store.qs_view.db_id = pg_database.oid \
            where start_time >= '%s' and start_time < '%s' \
            group by group_by, query_sql_text, start_time, datname order by datname,group_by, start_time ) \
            select datname as database_name,group_by, query_sql_text, array_agg(metric) as metric_value, array_agg(start_time) as timeseries \
            from ordered_qs_aggregation group by datname, group_by, query_sql_text"
        conn = self.get_connection(self.get_secret_value(self.environment_name))
        cursor = self.get_cursor(conn)


        #ws
        #cursor.execute(ws_metric_aggregation_grouped_by % (baseline_period_start,baseline_period_end))
        #baseline = pd.DataFrame(cursor.fetchall(), columns=['db_id', 'group_by', 'metric_distribution'])

        #cursor.execute(ws_metric_aggregation_grouped_by % (current_period_start,current_period_end))
        #current = pd.DataFrame(cursor.fetchall(), columns=['db_id', 'group_by', 'metric_distribution'])

        #qs
        cursor.execute(qs_metric_aggregation_grouped_by % ('sum','mean_time',baseline_period_start,baseline_period_end))
        baseline = pd.DataFrame(cursor.fetchall(), columns=['database_name', 'group_by','description', 'metric_distribution','timeseries'])

        cursor.execute(qs_metric_aggregation_grouped_by % ('sum','mean_time',current_period_start,current_period_end))
        current = pd.DataFrame(cursor.fetchall(), columns=['database_name', 'group_by','description', 'metric_distribution','timeseries'])

        self.commit_close(conn,cursor)

        if(len(baseline.index)>0 and len(current.index)>0):
            comparison_frame = pd.merge(baseline, current, how='right', left_on=['database_name','group_by'],right_on=['database_name', 'group_by'])
        
            row_count = len(comparison_frame.index)
            i = 0
            pdf = matplotlib.backends.backend_pdf.PdfPages("./docs/output.pdf")

            for index, row in comparison_frame.iterrows():
                query_id = comparison_frame.iloc[index,1]
                database_name = comparison_frame.iloc[index,0]
                query_text = comparison_frame.iloc[index,2]

                #create distribution of metrics from query store per query for baseline period and current period
                b = np.asarray(comparison_frame.iloc[index,3])
                c = np.asarray(comparison_frame.iloc[index,6])

                # Compute the descriptive statistics of baseline (b) and current(c)
                bbar = b.mean()
                bvar = b.var(ddof=1)
                nb = b.size
                bdof = nb - 1

                cbar = c.mean()
                cvar = c.var(ddof=1)
                nc = c.size
                cdof = nc - 1

                if (bdof<=0 or cdof<=0):
                    continue
                if (nb<30 or nc<30):
                    #not enough population size for central limit theorem to hold
                    continue
                if (directional_preference*(cbar-bbar)<0):
                    continue
                if((abs(cbar-bbar)/bbar)<percent_change_threshold):
                    continue
                    
                # Use scipy.stats.ttest_ind's welch's test
                t, p = ttest_ind(b, c, equal_var=False, nan_policy = 'omit')
                one_sided_p = p/2
                if(one_sided_p > p_threshold):
                    result = 'failed to reject h0: no difference significance (query_id: %s database_name: %s) ' % (query_id,database_name)
                elif (one_sided_p < p_threshold):
                    i = i + 1
                    result = 'rejected h0: difference significance (query_id: %s database_name: %s) ' % (query_id,database_name)
                    baseline_series = pd.Series.from_array(comparison_frame.iloc[index,3],comparison_frame.iloc[index,4])
                    current_series = pd.Series.from_array(comparison_frame.iloc[index,6],comparison_frame.iloc[index,7])

                    fig, ax1 = plt.subplots(figsize=(10,4))
                    baseline_series.plot(ax=ax1)

                    current_series.plot(ax=ax1)
                    fig.text(0,0.5,'Query ID: %s\n\nDatabase: %s\n\nQuery Text (first 100): %s\n\n\np-value:%s'%(comparison_frame.iloc[index,1],comparison_frame.iloc[index,0],comparison_frame.iloc[index,2][:100],p),ha='right',va='top')
                    
                    plt.legend (loc='best')
                    pdf.savefig(fig, bbox_inches='tight')

                else:
                    result = 'nan: omit processing (query_id: %s database_name: %s) ' % (query_id,database_name)
                self.logging.info(result)
                self.logging.info("Row: %s of %s processed. count of series with significant difference:%s " %(index+1,row_count,i))

            pdf.close()
            pdfs['output'] = pdf

            return pdfs
        else:
            self.logging.info('No records exist in one or more periods you specified. Please select ranges for which both baseline and current data exists')
            return None
