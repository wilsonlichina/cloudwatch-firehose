# CloudWatch Metrics Processing Pipeline

This CloudFormation template creates a complete serverless solution for processing CloudWatch metrics through multiple AWS services.

这个CloudFormation模板创建了一个完整的serverless解决方案，用于通过多个AWS服务处理CloudWatch指标。

## 系统架构 (System Architecture)

系统将自动创建一个完整的serverless处理管道：
CloudWatch → Metric Stream → Firehose → Lambda处理器 → API Gateway → Lambda HTTP Endpoint

The solution implements the following processing pipeline:

1. CloudWatch Metric Stream:
   - 输出格式设置为JSON (Output format set to JSON)
   - 配置为将指标发送到Kinesis Firehose (Configured to send metrics to Kinesis Firehose)
   - 包含AWS/EC2、AWS/Lambda和AWS/RDS命名空间的指标 (Includes metrics from AWS/EC2, AWS/Lambda, and AWS/RDS namespaces)

2. Kinesis Firehose:
   - 源类型设置为Direct PUT (Source type set to Direct PUT)
   - 目标设置为自托管的HTTP endpoint (Destination set to self-hosted HTTP endpoint via API Gateway)
   - 使用Lambda函数进行记录转换 (Uses Lambda for record transformation)
   - 配置了失败记录的S3备份 (Configured S3 backup for failed records)

3. Lambda Functions:
   - Record Processor:
     * 转换和丰富指标数据 (Transforms and enriches metric data)
     * 添加处理时间戳 (Adds processing timestamp)
     * 规范化指标值 (Normalizes metric values)
     * 包含错误处理和日志记录 (Includes error handling and logging)
   
   - HTTP Endpoint:
     * 接收和处理最终数据 (Receives and processes final data)
     * 添加接收时间戳 (Adds receipt timestamp)
     * 跟踪处理状态 (Tracks processing status)

4. API Gateway:
   - REST API配置 (REST API configuration)
   - POST方法接收指标 (POST method for receiving metrics)
   - Lambda代理集成 (Lambda proxy integration)
   - 自动生成HTTPS endpoint URL (Auto-generated HTTPS endpoint URL)

## 创建的资源 (Resources Created)

- CloudWatch Metric Stream
- Kinesis Firehose Delivery Stream
- Lambda函数 (Lambda Functions):
  * Record Processor
  * HTTP Endpoint
- API Gateway REST API
- S3存储桶 (S3 Buckets):
  * Lambda代码存储 (Lambda code storage)
  * Firehose失败记录备份 (Firehose backup for failed records)
- IAM角色和策略 (IAM Roles and Policies)

## 部署说明 (Deployment Instructions)

为了确保成功部署，请按照以下步骤操作。模板需要以下参数 (The template requires the following parameters):

- LambdaS3Bucket: Lambda函数代码所在的S3存储桶名称 (S3 bucket name containing Lambda function code)
- LambdaS3Key: Record Processor Lambda函数代码的S3键，默认为'lambda/record_processor.zip' (S3 key for Record Processor Lambda code)
- HttpEndpointLambdaS3Key: HTTP Endpoint Lambda函数代码的S3键，默认为'lambda/http_endpoint.zip' (S3 key for HTTP Endpoint Lambda code)

### 1. 准备S3存储桶 (Prepare S3 Bucket)

首先创建一个S3存储桶来存储Lambda函数代码：

```bash
# 创建唯一的S3存储桶名称 (Create unique S3 bucket name)
BUCKET_NAME="cloudwatch-firehose-lambda-code-$(date +%s)"

# 创建S3存储桶 (Create S3 bucket)
aws s3 mb s3://$BUCKET_NAME

# 记录存储桶名称供后续使用 (Note down bucket name for later use)
echo "Created bucket: $BUCKET_NAME"
```

### 2. 准备Lambda函数代码 (Prepare Lambda Function Code)

创建并上传Lambda函数的部署包：

```bash
# 进入Lambda代码目录 (Enter Lambda code directory)
cd src/lambda

# 创建部署包 (Create deployment packages)
zip -r record_processor.zip record_processor.py
zip -r http_endpoint.zip http_endpoint.py

# 上传到S3存储桶 (Upload to S3 bucket)
aws s3 cp record_processor.zip s3://$BUCKET_NAME/lambda/record_processor.zip
aws s3 cp http_endpoint.zip s3://$BUCKET_NAME/lambda/http_endpoint.zip
```

### 3. 部署CloudFormation堆栈 (Deploy CloudFormation Stack)

#### 使用AWS CLI部署 (Deploy using AWS CLI):

   ```bash
   # 创建堆栈 (Create stack)
   aws cloudformation create-stack \
     --stack-name cloudwatch-firehose-put-http \
     --template-body file://template.yaml \
     --capabilities CAPABILITY_IAM \
     --parameters \
       ParameterKey=LambdaS3Bucket,ParameterValue=$BUCKET_NAME \
       ParameterKey=LambdaS3Key,ParameterValue=lambda/record_processor.zip \
       ParameterKey=HttpEndpointLambdaS3Key,ParameterValue=lambda/http_endpoint.zip

   # 等待堆栈创建完成 (Wait for stack creation)
   aws cloudformation wait stack-create-complete \
     --stack-name cloudwatch-firehose-put-http

   # 验证部署状态 (Verify deployment status)
   aws cloudformation describe-stacks \
     --stack-name cloudwatch-firehose-put-http \
     --query 'Stacks[0].StackStatus' \
     --output text
   ```

#### 或通过AWS控制台部署 (Or Deploy via AWS Console):

1. 导航到CloudFormation控制台 (Navigate to CloudFormation console)
2. 选择"创建堆栈" (Choose "Create stack")
3. 上传template.yaml文件 (Upload template.yaml file)
4. 堆栈名称输入"cloudwatch-firehose-put-http" (Enter stack name)
5. 在参数页面填写以下信息 (Fill in the following parameters):
   - LambdaS3Bucket: 输入之前创建的S3存储桶名称 (Enter the S3 bucket name created earlier)
   - LambdaS3Key: 保持默认值 'lambda/record_processor.zip'
   - HttpEndpointLambdaS3Key: 保持默认值 'lambda/http_endpoint.zip'
6. 确认并创建堆栈 (Review and create stack)

### 4. 验证部署 (Verify Deployment)

部署完成后，验证关键组件：

```bash
# 获取API Gateway端点 (Get API Gateway endpoint)
aws cloudformation describe-stacks \
  --stack-name cloudwatch-firehose-put-http \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

### 常见问题解决 (Common Issues Resolution)

1. 如果遇到"NoSuchKey"错误：
   - 确保Lambda代码已正确上传到S3存储桶
   - 验证S3路径与template.yaml中的配置匹配
   - 检查IAM角色是否有正确的S3访问权限

2. 如果堆栈创建失败：
   ```bash
   # 查看失败原因
   aws cloudformation describe-stack-events \
     --stack-name cloudwatch-firehose-put-http \
     --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].ResourceStatusReason' \
     --output text
   ```

3. 清理资源 (Cleanup):
   ```bash
   # 删除堆栈
   aws cloudformation delete-stack \
     --stack-name cloudwatch-firehose-put-http

   # 等待删除完成
   aws cloudformation wait stack-delete-complete \
     --stack-name cloudwatch-firehose-put-http
   ```

## 输出值 (Outputs)

- MetricStreamArn: CloudWatch Metric Stream的ARN
- FirehoseArn: Kinesis Firehose的ARN
- FirehoseBackupBucketName: Firehose备份桶的名称
- LambdaCodeBucketName: Lambda代码存储桶的名称
- ApiEndpoint: API Gateway端点URL

## 故障排除 (Troubleshooting)

1. 查看Lambda日志 (View Lambda Logs):
   ```bash
   aws logs tail /aws/lambda/[stack-name]-record-processor
   aws logs tail /aws/lambda/[stack-name]-http-endpoint
   ```

2. 检查Firehose传输 (Check Firehose Delivery):
   - 检查FirehoseBackupBucket中的失败记录 (Review failed records in FirehoseBackupBucket)
   - 监控CloudWatch指标了解传输状态 (Monitor CloudWatch metrics for delivery status)

3. API Gateway问题 (API Gateway Issues):
   - 检查API Gateway日志 (Check API Gateway logs)
   - 验证端点URL和权限 (Verify endpoint URL and permissions)
