## Sequoia选股系统
### 简介
本程序使用[AKShare接口](https://github.com/akfamily/akshare)，从东方财富获取数据。

本程序实现了若干种选股策略，大家可以自行选择其中的一到多种策略组合使用，参见[work_flow.py](https://github.com/sngyai/Sequoia/blob/master/work_flow.py#L28-L38)，也可以实现自己的策略。

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
 ### 更新akshare数据接口
 本项目已切换至akshare数据接口，该项目更新频率较高，使用前建议检查接口更新
``` 
pip install akshare --upgrade
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
#### 定时任务
服务器端运行需要改为定时任务，共有两种方式：
1. 使用Python schedule定时任务
   * 将[config.yaml](config.yaml.example)中的`cron`配置改为`true`，`push`.`enable`改为`true`

2. 使用crontab定时任务
   * 保持[config.yaml](config.yaml.example)中的`cron`配置为***false***，`push`.`enable`为`true`
   * [安装crontab](https://www.digitalocean.com/community/tutorials/how-to-use-cron-to-automate-tasks-ubuntu-1804)
   * `crontab -e` 添加如下内容(服务器端安装了miniconda3)：
   ```bash
    SHELL=/bin/bash
    PATH=/usr/bin:/bin:/home/ubuntu/miniconda3/bin/
    # m h  dom mon dow   command
    0 3 * * 1-5 source /home/ubuntu/miniconda3/bin/activate python3.10; python3 /home/ubuntu/Sequoia/main.py >> /home/ubuntu/Sequoia/sequoia.log; source /home/ubuntu/miniconda3/bin/deactivate
   ```
#### 微信推送
使用[WxPusher](https://wxpusher.zjiecode.com/docs/#/)实现了微信推送，用户需要自行获取[wxpusher_token](https://wxpusher.zjiecode.com/docs/#/?id=%e8%8e%b7%e5%8f%96apptoken)和[wxpusher_uid](https://wxpusher.zjiecode.com/docs/#/?id=%e8%8e%b7%e5%8f%96uid)，并配置到`config.yaml`中去。


## 如何回测
修改[config.yaml](config.yaml.example)中`end_date`为指定日期，格式为`'YYYY-MM-DD'`，如：
```
end = '2019-06-17'
```

