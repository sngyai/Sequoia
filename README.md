## Sequoia选股系统
### 简介
本程序使用传统的[TuShare接口](http://tushare.org/)，并非需要捐赠的[pro接口](https://tushare.pro/)，获取数据无限制;

另，由于TuShare的增量更新接口有bug（最近一个交易日的数据获取不到），所以每次计算前都是删除所有数据，全部重新获取。

本程序实现了若干种选股策略，大家可以自行选择其中的一到多种策略组合使用，参见[work_flow.py](https://github.com/sngyai/Sequoia/blob/master/work_flow.py#L41-L48)

各策略中的`end_date`参数主要用于回测。

## 安装依赖:
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
 ### 推荐使用Python3.5以上以及pip3
 ### Python 依赖:
 ```
 pip install -r requirements.txt 
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
* 参考[README_PUSH.md](README_PUSH.md)文档搭建 [ejabberd](https://github.com/processone/ejabberd) 推送服务
* 客户端Android推荐使用 [Conversations](https://github.com/siacs/Conversations) ，iOS没有开发者证书的话推送不了，有证书推荐使用 [ChatSecure-iOS
](https://github.com/ChatSecure/ChatSecure-iOS) ，我采用的推送方案是`ejabberd`搭配`Conversations`。
效果如图

![statistics](images/statistics.jpg?raw=true "统计信息") ![strategy](images/strategy.jpg?raw=true "策略选股")

## 如何回测

修改 [work_flow.py#L61](https://github.com/sngyai/Sequoia/blob/master/work_flow.py#L61) 中`end`为指定日期，格式为`'YYYY-MM-DD'`，如：
```
end = '2019-06-17'
```
