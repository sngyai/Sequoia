## Sequoia投资系统
#### 安装依赖:
 * 根据不同的平台安装TA-Lib程序

##### Mac OS X

```
$ brew install ta-lib
```

##### Windows

下载 [ta-lib-0.4.0-msvc.zip](http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-msvc.zip)
解压到 ``C:\ta-lib``



##### Linux

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