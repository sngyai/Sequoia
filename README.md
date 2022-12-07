## Sequoia选股系统
### 简介
本程序使用传统的[AKShare接口](https://github.com/akfamily/akshare)

本程序实现了若干种选股策略，大家可以自行选择其中的一到多种策略组合使用，参见[work_flow.py](https://github.com/sngyai/Sequoia/blob/master/work_flow.py#L28-L36)，也可以实现自己的策略。

各策略中的`end_date`参数主要用于回测。

## 准备工作:
 ### 根据不同的平台安装TA-Lib程序

* Mac OS X

    ```
    $ brew install ta-lib
    ```

* Windows

    下载 [ta-lib-0.4.0-msvc.zip](http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-msvc.zip)，解压到 ``C:\ta-lib``



* Linux

    下载 [ta-lib-0.4.0-src.tar.gz](http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz) :
    ```
    $ untar and cd
    $ ./configure --prefix=/usr
    $ make
    $ sudo make install
    ```
 ### 推荐使用Python3.8以上以及pip3
 ### Python 依赖:
 ```
 pip install -r requirements.txt 
 ```

 ### 生成配置文件

```
cp config.yaml.example config.yaml
```
## 运行
### 本地运行
```
$ python main.py
```
运行结果查看日志文件[sequoia.log](sequoia.log)

### 服务器端运行
用户也可以将本程序作为定时任务运行在服务端，需要做以下工作：
* 将[config.yaml](config.yaml)中的`cron`配置改为`true`，`push`.`enable`改为true
* 使用[WxPusher](https://wxpusher.zjiecode.com/docs/#/)实现了微信推送，用户需要自行获取[wxpusher_token](https://wxpusher.zjiecode.com/docs/#/?id=%e8%8e%b7%e5%8f%96apptoken)和[wxpusher_uid](https://wxpusher.zjiecode.com/docs/#/?id=%e8%8e%b7%e5%8f%96uid)，并配置到`config.yaml`中去。
## 如何回测

修改 `config.yaml` 中`end_date`为指定日期，格式为`'YYYY-MM-DD'`，如：
```
end = '2019-06-17'
```
