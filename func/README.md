# Azure Functions

Serverless Azure Functions for the Trovesuite ERP Core Platform. These functions handle background jobs, event-driven operations, and scheduled tasks.

## 📁 Directory Structure

```
func/
├── function_app.py       # Main Azure Functions application
├── host.json             # Functions host configuration
├── local.settings.json   # Local development settings
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🏗️ Architecture

Azure Functions provide serverless compute for:
- **Background Jobs**: Asynchronous processing
- **Event-Driven Tasks**: Triggered by database changes, messages, etc.
- **Scheduled Tasks**: Cron-like scheduled operations
- **Webhooks**: External system integrations

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Azure Functions Core Tools v4
- Azure subscription (for deployment)
- Azure Storage Account (for function state)

### Install Azure Functions Core Tools

**macOS:**
```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
```

**Windows:**
```bash
npm install -g azure-functions-core-tools@4
```

**Linux:**
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4
```

### Install Dependencies

```bash
cd func
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Local Development

1. **Configure Local Settings**:
Edit `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "DB_HOST": "localhost",
    "DB_PORT": "5431",
    "DB_NAME": "erpdb",
    "DB_USER": "user",
    "DB_PASSWORD": "password",
    "ENVIRONMENT": "development"
  }
}
```

2. **Start Functions Host**:
```bash
func start
```

3. **Test Functions**:
```bash
# HTTP trigger
curl http://localhost:7071/api/function_name

# Timer trigger (runs automatically)
# Queue trigger (add message to queue)
```

## 📝 Function Types

### HTTP Trigger Functions

HTTP-triggered functions respond to HTTP requests:

```python
import azure.functions as func
import logging

app = func.FunctionApp()

@app.route(route="http_trigger")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')
    
    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
            status_code=200
        )
```

### Timer Trigger Functions

Scheduled functions that run on a cron schedule:

```python
import azure.functions as func
import datetime

@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False)
def timer_trigger(myTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
```

**Schedule Format:**
- `0 */5 * * * *` - Every 5 minutes
- `0 0 * * * *` - Every hour
- `0 0 0 * * *` - Daily at midnight
- `0 0 0 * * 0` - Weekly on Sunday

### Queue Trigger Functions

Functions triggered by Azure Queue Storage messages:

```python
@app.queue_trigger(arg_name="msg", queue_name="myqueue",
                               connection="AzureWebJobsStorage")
def queue_trigger(msg: func.QueueMessage) -> None:
    logging.info('Python Queue trigger processed a message: %s',
                msg.get_body().decode('utf-8'))
```

### Blob Trigger Functions

Functions triggered by blob storage changes:

```python
@app.blob_trigger(arg_name="myblob", path="samples-workitems/{name}",
                               connection="AzureWebJobsStorage")
def blob_trigger(myblob: func.InputStream):
    logging.info(f'Python blob trigger function processed blob \n'
                f'Name: {myblob.name}\n'
                f'Blob Size: {myblob.length} bytes')
```

## 🔧 Configuration

### host.json

Global configuration for all functions:

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "maxTelemetryItemsPerSecond": 20
      }
    },
    "logLevel": {
      "default": "Information",
      "Host.Results": "Error",
      "Function": "Error",
      "Host.Aggregator": "Trace"
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  },
  "functionTimeout": "00:05:00",
  "retry": {
    "strategy": "fixedDelay",
    "maxRetryCount": 2,
    "delayInterval": "00:00:05"
  }
}
```

### function.json (per function)

Individual function configuration:

```json
{
  "scriptFile": "function_app.py",
  "bindings": [
    {
      "name": "req",
      "type": "httpTrigger",
      "direction": "in",
      "authLevel": "function",
      "methods": ["get", "post"]
    },
    {
      "name": "$return",
      "type": "http",
      "direction": "out"
    }
  ]
}
```

## 🔐 Authentication

### Function Key Authentication

Functions can be protected with keys:

```python
@app.route(route="secure_function", auth_level=func.AuthLevel.FUNCTION)
def secure_function(req: func.HttpRequest) -> func.HttpResponse:
    # Function requires valid function key
    return func.HttpResponse("Secure function executed")
```

### Managed Identity

Use Azure Managed Identity for accessing other Azure resources:

```python
from azure.identity import ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

credential = ManagedIdentityCredential()
client = SecretClient(vault_url="https://myvault.vault.azure.net/", credential=credential)

secret = client.get_secret("db-password")
```

## 📊 Monitoring & Logging

### Application Insights

Enable Application Insights for monitoring:

```json
// local.settings.json
{
  "Values": {
    "APPINSIGHTS_INSTRUMENTATIONKEY": "your-instrumentation-key"
  }
}
```

### Structured Logging

```python
import logging
import json

def my_function(req: func.HttpRequest) -> func.HttpResponse:
    logger = logging.getLogger()
    
    # Structured logging
    log_data = {
        "function": "my_function",
        "request_id": req.headers.get('x-request-id'),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    
    logger.info(json.dumps(log_data))
    
    return func.HttpResponse("Success")
```

## 🗄️ Database Integration

### Using PostgreSQL

```python
import psycopg2
import os

def process_data(req: func.HttpRequest) -> func.HttpResponse:
    # Get database connection string
    conn_string = f"host={os.environ['DB_HOST']} " \
                  f"port={os.environ['DB_PORT']} " \
                  f"dbname={os.environ['DB_NAME']} " \
                  f"user={os.environ['DB_USER']} " \
                  f"password={os.environ['DB_PASSWORD']}"
    
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    
    try:
        # Execute query
        cursor.execute("SELECT * FROM users WHERE is_active = %s", (True,))
        results = cursor.fetchall()
        
        return func.HttpResponse(f"Processed {len(results)} users")
    finally:
        cursor.close()
        conn.close()
```

## 🚀 Deployment

### Deploy to Azure

1. **Login to Azure**:
```bash
az login
az account set --subscription "your-subscription-id"
```

2. **Create Function App**:
```bash
az functionapp create \
  --resource-group myResourceGroup \
  --consumption-plan-location westus \
  --runtime python \
  --runtime-version 3.12 \
  --functions-version 4 \
  --name myFunctionApp \
  --storage-account mystorageaccount
```

3. **Deploy Function**:
```bash
func azure functionapp publish myFunctionApp
```

### CI/CD with Azure DevOps

Add to `azure-pipelines.yml`:

```yaml
- stage: DeployFunctions
  displayName: 'Deploy Azure Functions'
  jobs:
  - job: Deploy
    displayName: 'Deploy Functions'
    steps:
    - task: AzureFunctionApp@1
      inputs:
        azureSubscription: 'your-subscription'
        appType: 'functionAppLinux'
        appName: 'myFunctionApp'
        package: '$(System.DefaultWorkingDirectory)/func'
```

## 📦 Dependencies

Key dependencies in `requirements.txt`:

```
azure-functions==1.18.0
azure-identity==1.15.0
azure-keyvault-secrets==4.7.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
requests==2.31.0
```

## 🔧 Common Use Cases

### 1. Scheduled Data Cleanup

```python
@app.timer_trigger(schedule="0 0 2 * * *", arg_name="myTimer")
def cleanup_old_data(myTimer: func.TimerRequest) -> None:
    # Clean up soft-deleted records older than 90 days
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM users 
        WHERE delete_status = 'DELETED' 
        AND cdatetime < NOW() - INTERVAL '90 days'
    """)
    
    conn.commit()
    logging.info(f"Cleaned up {cursor.rowcount} old records")
```

### 2. Email Notifications

```python
@app.queue_trigger(arg_name="msg", queue_name="email-queue")
def send_email(msg: func.QueueMessage) -> None:
    email_data = json.loads(msg.get_body().decode('utf-8'))
    
    # Send email using SendGrid, etc.
    send_email_notification(
        to=email_data['to'],
        subject=email_data['subject'],
        body=email_data['body']
    )
```

### 3. Report Generation

```python
@app.timer_trigger(schedule="0 0 9 * * 1", arg_name="myTimer")
def generate_weekly_report(myTimer: func.TimerRequest) -> None:
    # Generate weekly reports every Monday at 9 AM
    report_data = fetch_report_data()
    report_file = generate_pdf_report(report_data)
    
    # Upload to blob storage
    upload_to_storage(report_file, f"reports/weekly_{datetime.date.today()}.pdf")
```

### 4. Data Synchronization

```python
@app.blob_trigger(arg_name="myblob", path="imports/{name}")
def sync_data(myblob: func.InputStream):
    # Process uploaded data file
    data = json.loads(myblob.read())
    
    # Sync to database
    sync_to_database(data)
    
    logging.info(f"Synced data from {myblob.name}")
```

## 🐛 Troubleshooting

### Local Development Issues

1. **Port Already in Use**:
```bash
# Find process using port 7071
lsof -ti:7071 | xargs kill
```

2. **Python Version Mismatch**:
```bash
# Check Python version
python --version

# Should be 3.12 or 3.13
```

3. **Storage Emulator Issues**:
```bash
# Start Azure Storage Emulator
azurite --silent --location ~/azurite --debug ~/azurite/debug.log
```

### Deployment Issues

1. **Check Function Logs**:
```bash
az functionapp log tail --name myFunctionApp --resource-group myResourceGroup
```

2. **Test Function**:
```bash
az functionapp function show --name myFunctionApp --resource-group myResourceGroup --function-name my_function
```

3. **View Metrics**:
```bash
az monitor metrics list --resource myFunctionApp --metric FunctionExecutionCount
```

## 🔒 Security Best Practices

1. **Use Managed Identity** for Azure resource access
2. **Store secrets in Key Vault**, not in code
3. **Enable HTTPS only** for HTTP functions
4. **Use function keys** for authentication
5. **Implement rate limiting** for public endpoints
6. **Log security events** for auditing
7. **Regular security updates** for dependencies

## 📚 Additional Resources

- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Python Developer Guide](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [Azure Functions Best Practices](https://docs.microsoft.com/azure/azure-functions/functions-best-practices)
- [Azure Functions Pricing](https://azure.microsoft.com/pricing/details/functions/)

## 🤝 Contributing

When adding new functions:
1. Follow naming conventions
2. Add comprehensive logging
3. Handle errors gracefully
4. Document function purpose
5. Add tests where applicable
6. Update this README

## 📄 License

Proprietary - Trovesuite ERP Platform


