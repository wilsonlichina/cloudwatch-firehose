# CloudWatch指标流到Kinesis Firehose (CloudWatch Metric Streams to Kinesis Firehose)

此 CloudFormation 模板部署了一个无服务器架构，用于将 CloudWatch 指标数据通过 Kinesis Data Firehose 实时传输至 VPC 内的私有 HTTP 端点。处理流程为CloudWatch → Metric Stream → Kinesis Data Firehose（VPC）→ API Gateway（VPC）→ Lambda Functions。

## 系统架构 (System Architecture)

该解决方案实现了以下处理流程：

1. CloudWatch指标流 (CloudWatch Metric Stream):
   - 输出格式为JSON (Output format set to JSON)
   - 配置为将指标发送到Kinesis Firehose (Configured to send metrics to Kinesis Firehose)
   - 包含AWS/EC2、AWS/Lambda和AWS/RDS命名空间的指标 (Includes metrics from AWS/EC2, AWS/Lambda, and AWS/RDS namespaces)

2. Kinesis数据传输流 (Kinesis Firehose):
   - 源类型设置为Direct PUT (Source type set to Direct PUT)
   - 使用Lambda函数进行记录转换 (Uses Lambda function for record transformation)
   - 目标设置为私有API Gateway端点 (Destination set to private API Gateway endpoint)
   - 配置了失败记录的S3备份 (Configured S3 backup for failed records)
   - 通过VPC端点访问 (Accessed via VPC Endpoint)

3. Lambda函数 (Lambda Functions):
   - 记录处理器 (Record Processor):
     * 转换传入的Firehose记录 (Transforms incoming Firehose records)
     * 处理和丰富指标数据 (Processes and enriches metric data)
   - HTTP端点 (HTTP Endpoint):
     * 接收处理后的指标 (Receives processed metrics)
     * 处理最终数据 (Handles final data processing)

4. API Gateway私有端点 (API Gateway Private Endpoint):
   - 配置为私有API (Configured as private API)
   - 仅在VPC内部可访问 (Only accessible within VPC)
   - 通过VPC端点访问 (Accessed via VPC Endpoint)
   - POST方法接收指标 (POST method for receiving metrics)
   - Lambda代理集成 (Lambda proxy integration)

5. VPC端点 (VPC Endpoints):
   - API Gateway VPC端点:
     * 允许VPC内部访问API Gateway (Allows VPC internal access to API Gateway)
     * 接受来自Firehose的请求 (Accepts requests from Firehose)
   - Kinesis Firehose VPC端点:
     * 允许VPC内部访问Firehose服务 (Allows VPC internal access to Firehose service)

6. 安全组 (Security Groups):
   - VPC端点安全组:
     * 允许HTTPS (443)入站流量 (Allows HTTPS (443) inbound traffic)
   - Firehose端点安全组:
     * 允许HTTPS (443)入站流量 (Allows HTTPS (443) inbound traffic)

## 部署前提条件 (Prerequisites)

在部署此模板之前，请确保您具备：

1. VPC配置要求:
   - 至少一个私有子网 (At least one private subnet)
   - 启用DNS主机名和DNS解析 (DNS hostnames and DNS resolution enabled)
   - 足够的可用IP地址 (Sufficient available IP addresses)

2. 已安装并配置AWS CLI，具有以下权限:
   - CloudFormation
   - IAM
   - VPC
   - Lambda
   - API Gateway
   - Kinesis Firehose
   - S3

## 部署步骤 (Deployment Steps)

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

#### 使用AWS CLI部署:

```bash
# 部署堆栈 (Deploy stack)
aws cloudformation create-stack \
  --stack-name cloudwatch-firehose \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_IAM \
  --parameters \
    ParameterKey=VpcId,ParameterValue=<your-vpc-id> \
    ParameterKey=PrivateSubnetIds,ParameterValue=<subnet1>,<subnet2> \
    ParameterKey=LambdaS3Bucket,ParameterValue=$BUCKET_NAME \
    ParameterKey=LambdaS3Key,ParameterValue=lambda/record_processor.zip \
    ParameterKey=HttpEndpointLambdaS3Key,ParameterValue=lambda/http_endpoint.zip

# 等待堆栈创建完成 (Wait for stack creation)
aws cloudformation wait stack-create-complete \
  --stack-name cloudwatch-firehose

# 验证部署状态 (Verify deployment status)
aws cloudformation describe-stacks \
  --stack-name cloudwatch-firehose \
  --query 'Stacks[0].StackStatus' \
  --output text
```

#### 使用AWS控制台部署:

1. 导航到CloudFormation控制台
2. 选择"创建堆栈"
3. 上传template.yaml文件
4. 堆栈名称输入"cloudwatch-firehose"
5. 在参数页面填写以下信息:
   - VpcId: 选择要部署的VPC
   - PrivateSubnetIds: 选择私有子网
   - LambdaS3Bucket: 输入之前创建的S3存储桶名称
   - LambdaS3Key: 输入'lambda/record_processor.zip'
   - HttpEndpointLambdaS3Key: 输入'lambda/http_endpoint.zip'
6. 确认并创建堆栈

### 4. 验证部署 (Verify Deployment)

部署完成后，验证关键组件：

```bash
# 获取API Gateway端点
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name cloudwatch-firehose \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)
echo "API端点: $API_ENDPOINT"

# 获取Firehose ARN
FIREHOSE_ARN=$(aws cloudformation describe-stacks \
  --stack-name cloudwatch-firehose \
  --query 'Stacks[0].Outputs[?OutputKey==`FirehoseArn`].OutputValue' \
  --output text)
echo "Firehose ARN: $FIREHOSE_ARN"
```

## 故障排除 (Troubleshooting)

1. 堆栈创建失败:
   ```bash
   # 查看失败原因
   aws cloudformation describe-stack-events \
     --stack-name cloudwatch-firehose \
     --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].ResourceStatusReason' \
     --output text
   ```

2. Lambda函数问题:
   ```bash
   # 查看Lambda日志
   aws logs tail /aws/lambda/cloudwatch-firehose-record-processor
   aws logs tail /aws/lambda/cloudwatch-firehose-http-endpoint
   ```

3. Firehose传输问题:
   - 检查FirehoseBackupBucket中的失败记录
   - 验证VPC端点连接性
   - 检查CloudWatch日志

4. VPC配置问题:
   - 确保私有子网有正确的路由配置
   - 验证VPC端点的DNS设置
   - 检查安全组规则

## 清理资源 (Cleanup)

删除所有创建的资源：

```bash
# 删除堆栈
aws cloudformation delete-stack \
  --stack-name cloudwatch-firehose

# 等待删除完成
aws cloudformation wait stack-delete-complete \
  --stack-name cloudwatch-firehose

# 删除S3存储桶
aws s3 rm s3://$BUCKET_NAME --recursive
aws s3 rb s3://$BUCKET_NAME
