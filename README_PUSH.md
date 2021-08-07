# 配置推送服务
本文档用于记录，稍显啰嗦乏味，没有推送需求可以略过不看。

## 环境
* 服务器：Ubuntu 18.04
* 客户端：Android手机

## 服务器端

* 安装ejabberd
```
wget https://static.process-one.net/ejabberd/downloads/21.07/ejabberd-21.07-linux-x64.run
chmod +x ejabberd-21.07-linux-x64.run
```
安装过程需要一系列的配置，需要特别关注的地方包括安装路径，管理员ID

* 使用域名，启用SSL

自行去云服务商注册域名和申请证书，过程可以参考 [域名注册](https://docs.ucloud.cn/udnr/operate/register) 以及 [证书快速申请流程指南](https://docs.ucloud.cn/ussl/operate/simple) ，本例中域名为`example.com`。

下载证书，以UCloud下载的原始证书为例，其中包括三个文件`ca.cert`、`private.key`、`public.crt`
```
cp ca.cert ca.pem
cat ca.cert private.key public.crt > ejabberd.pem
```
上传`ca.pem`与`ejabberd.pem`到服务器端，放到ejabberd安装路径下的conf目录
修改conf/ejabberd.yml中的`certfiles`与`ca_file`
```
certfiles:
  - "/home/ubuntu/ejabberd-21.07/conf/ejabberd.pem"
```

```
ca_file: "/home/ubuntu/ejabberd-21.07/conf/ca.pem"
```

其中的`/home/ubuntu/ejabberd-21.07/`为ejabberd安装路径

* 启动服务

在安装路径下执行

```
bin/ejabberdctl start
```

查看日志有无error

```
tail -f logs/error.log
```

* 添加账号

```
bin/ejabberdctl register ${admin} example.com ${管理员自定义密码}
```

其中admin对应安装引导中设置的管理员，后面会用到；
注册普通账号命令相同

```
bin/ejabberdctl register ${user} example.com ${用户自定义密码}
```

* 登录后台管理

浏览器访问`http://example.com:5280/admin`，输入注册管理员账号时候的用户名密码(上面的${admin}和${自定义密码})


## 手机端

* 下载源码 

```
git clone https://github.com/inputmice/Conversations.git
```

* 编译APK

使用Android Studio导入项目

打开`build.gradle`，注释掉
```
implementation fileTree(include: ['libwebrtc-m90.aar'], dir: 'libs')
```

添加
```
implementation 'org.webrtc:google-webrtc:1.0.32006'
```

点击Android Studio菜单`Build`、`Generate Signed Bundle/APK...`，生成后会提示APK所在目录，传到手机安装

## 运行手机App

打开Conversations，点击“我已有帐户”
`XMPP地址`填`${user}@example.com`，密码填`${用户自定义密码}`

没有意外就登录成功了，可以再添加个账户，两个账户在手机上互撩体验一下

## 调用ejabberd ReST API推送消息

根据上述配置，修改[config.yaml](config.yaml)中的`push`相关配置