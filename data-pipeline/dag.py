import airflow
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator

import requests
from datetime import datetime

import smtplib 
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText 
from email.mime.base import MIMEBase 
from email import encoders


EMAIL_DETAILS = {
    'fromaddr' : 'freelance.arnav@gmail.com',
    'pwd' : 'qWeRtYuIoP10', # if using gmail, please head to myaccount.google.com/lesssecureapps and enable the option
    'toaddr' : 'arnavkohli@gmail.com'
}

args = {
    'owner': 'Airflow',
    'start_date': airflow.utils.dates.days_ago(2),
    'schedule_interval': '@daily'
}

dag = DAG(
    dag_id='tmdb_data_pipeline',
    default_args=args
)

def clean(dtime):
    m = dtime.month
    d = dtime.day
    y = dtime.year

    if len(str(m)) != 2:
        m = '0' + str(m)
    if len(str(d)) != 2:
        d = '0' + str(d)

    m, d, y = map(str, (m, d, y))
    return m, d, y

def mail(fromaddr, pwd, toaddr, subject, filename):

    name = filename.split('.')[0]
    # instance of MIMEMultipart 
    msg = MIMEMultipart() 
      
    # storing the senders email address   
    msg['From'] = fromaddr 
      
    # storing the receivers email address  
    msg['To'] = toaddr 
      
    # storing the subject  
    msg['Subject'] = subject
      
    # string to store the body of the mail 
    line = '-'*20
    body = '{}\n\nThis is an automated task.\n\n{}\n\n'.format(line, line)
      
    # attach the body with the msg instance 
    msg.attach(MIMEText(body, 'plain')) 
      
    # open the file to be sent  
    attachment = open('./{}'.format(filename), "rb")    
    # instance of MIMEBase and named as p 
    p = MIMEBase('application', 'octet-stream') 
      
    # To change the payload into encoded form 
    p.set_payload((attachment).read()) 
      
    # encode into base64 
    encoders.encode_base64(p) 
       
    p.add_header('Content-Disposition', "attachment; filename= %s" % filename) 
      
    # attach the instance 'p' to instance 'msg' 
    msg.attach(p) 
      
    # creates SMTP session 
    s = smtplib.SMTP('smtp.gmail.com', 587) 
      
    # start TLS for security 
    s.starttls() 
      
    # Authentication 
    s.login(fromaddr, pwd) 
      
    # Converts the Multipart msg into a string 
    text = msg.as_string() 
      
    # sending the mail 
    s.sendmail(fromaddr, toaddr, text) 
      
    # terminating the session 
    s.quit() 

    print ('Data for `{}` sent to {}'.format(name, toaddr))

# push function
def download_data(**kwargs):

    current = datetime.now()
    month, day, year = clean(current)

    titles = {
        'movie',
        'tv_series',
        'person',
        'collection',
        'tv_network',
        'keyword',
        'production_company'
    }

    data = {

    }

    errors = {

    }

    for title in titles:
        base = 'http://files.tmdb.org/p/exports/{}_ids_{}_{}_{}.json.gz'.format(title, month, day, year)
        url = base.format(month, day, year)
        name = url.split('/')[-1]

        req  = requests.get(url)

        if req.status_code == 200:
            with open('./{}'.format(name), 'wb') as f:
                f.write(req.content)

            data[title] = name
        else:
            print ('DOWNLOAD ERROR: {}'.format(url))
            errors[title] = url

    current_dtime = {
        'month' : month,
        'day' : day,
        'year' : year
    }

    return data, current_dtime, errors


# pull function
def send_emails(**context):

    files, current_dtime, errors = context['task_instance'].xcom_pull(task_ids='download_data')

    fromaddr = EMAIL_DETAILS['fromaddr']
    pwd = EMAIL_DETAILS['pwd']
    toaddr = EMAIL_DETAILS['toaddr']
    
      
    # open the file to be sent  
    for title in files:
        filename = files[title]
        name = filename.split('.')[0]
        subject = "{} data for {}/{}/{}".format(name, current_dtime['month'], current_dtime['day'], current_dtime['year'])
        mail(
            fromaddr=fromaddr,
            pwd=pwd,
            toaddr=toaddr,
            subject=subject,
            filename=filename
        )
        

    return 'Emails sent to {}'.format(toaddr)

download_data_task = PythonOperator(
    task_id='download_data',
    python_callable=download_data,
    dag=dag,
)

send_emails_task = PythonOperator(
    task_id='send_emails',
    python_callable=send_emails,
    dag=dag,
    provide_context=True
)

download_data_task >> send_emails_task
