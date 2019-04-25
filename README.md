## Sequoia选股系统
### 简介
本程序使用传统的[TuShare接口](http://tushare.org/)，并非需要捐赠的[pro接口](https://tushare.pro/)，获取数据无限制;

另，由于TuShare的增量更新接口有bug（最近一个交易日的数据获取不到），所以每次计算前都是删除所有数据，全部重新获取。

本程序实现了若干种选股策略，大家可以自行选择其中的一到多种策略组合使用，参见[work_flow.py](https://github.com/sngyai/Sequoia/blob/master/work_flow.py#L33-L34)

各策略中的end_date参数主要用于回测。

选股的结果在日志文件sequoia.log中；

用户也可以将本程序作为定时任务运行在服务端，需要做以下工作：
* 注释掉[main.py](https://github.com/sngyai/Sequoia/blob/master/main.py#L26-L27)的L26-L27；
* 打开[main.py](https://github.com/sngyai/Sequoia/blob/master/main.py#L13-L24)中L13-L24的注释；
* 在[notify.py](notify.py)模块中实现自己的推送功能，每天定时将选股结果推送到手机上。

## 安装依赖:
 * 根据不同的平台安装TA-Lib程序

### Mac OS X

```
$ brew install ta-lib
```

### Windows

下载 [ta-lib-0.4.0-msvc.zip](http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-msvc.zip)
解压到 ``C:\ta-lib``



### Linux

下载 [ta-lib-0.4.0-src.tar.gz](http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz) :
```
$ untar and cd
$ ./configure --prefix=/usr
$ make
$ sudo make install
```
 * Python2.7或3.5以上
 * Python 依赖:
 ```
 pip install lxml requests bs4 numpy tushare pandas TA-Lib threadpool xlrd tables 
 ```
 
## 运行
```
$ python main.py
```
运行结果查看日志文件[sequoia.log](sequoia.log)
也可参考[notify.py](notify.py)模块，自行实现推送相关的功能
