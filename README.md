## Sequoia选股系统
### 简介
本程序使用[AKShare接口](https://github.com/akfamily/akshare)，从东方财富获取数据。

本程序实现了若干种选股策略，大家可以自行选择其中的一到多种策略组合使用，参见[work_flow.py](https://github.com/sngyai/Sequoia/blob/master/work_flow.py#L28-L38)，也可以实现自己的策略。

各策略中的`end_date`参数主要用于回测。

## 准备工作:
###  环境&依赖管理
推荐使用 Miniconda来进行 Python 环境管理 [Miniconda — conda documentation](https://docs.conda.io/en/latest/miniconda.html)

安装 conda 后，切换到项目专属环境进行配置，例如：
```
conda create -n sequoia39 python=3.9
conda activate sequoia39
```

 ### 根据不同的平台安装TA-Lib程序

* Mac OS X  (x86_64)

    ```  
    $ brew install ta-lib    
    # conda 环境下 可直接执行
    $ conda install -c conda-forge ta-lib
    ``` 

* Mac OS X (arm64)

    需要特殊说明的是
    M1 芯片的 Mac OS 很多库和依赖都需要基于 arm64 来构建。
    所以，这里首先需要确认安装的 homebrew 是 arm 版本，如果之前安装的 homebrew 是 x86 版本，推荐重装 homebrew。
  1. 删除老版本 homebrew （如果之前安装的是 x86版本 homebrew，重装前需要删除）
    ```
      sudo rm -rf /usr/local/.git
      rm -rf ~/Library/Caches/Homebrew
      rm -rf /usr/local/Homebrew 
    ```

  2. 安装/重装 arm64 版本 homebrew
    ```
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

   3. homebrew 初始化
    ```
    vim ~/.zshrc
    
    # 加入到系统环境变量
    export PATH=/opt/homebrew/bin:$PATH
    
    source ~/.zshrc
    # 确认版本信息
    brew config 
    ```
  4. 过程中遇到问题的参考解决办法
  - [macos - zsh problem: compinit:503: no such file or directory: /usr/local/share/zsh/site-functions/_brew - Stack Overflow](https://stackoverflow.com/questions/65747286/zsh-problem-compinit503-no-such-file-or-directory-usr-local-share-zsh-site)
  - [The required file "libmini_racer.dylib" can't be found in mac M1 · Issue #143 · sqreen/PyMiniRacer](https://github.com/sqreen/PyMiniRacer/issues/143)
  - [Installing python tables on mac with m1 chip - Stack Overflow](https://stackoverflow.com/questions/65839750/installing-python-tables-on-mac-with-m1-chip)

  5. 经过以上步骤后，可以开始继续安装 `ta-lib` 了。 参考
  - [TA-Lib · PyPI](https://pypi.org/project/TA-Lib/)
  - [说说 talib(ta-lib) 这个技术指标库，各系统怎么最轻松安装 ta-lib - 知乎](https://zhuanlan.zhihu.com/p/546720500)

  以下是完整的操作命令示例：

    ```
    # 操作示例
    # 1. 创建专属 python 环境
    conda create -n sequoia39 python=3.9
    conda activate sequoia39
    
    # 2. 安装 ta-lib 库
    arch -arm64 brew install ta-lib
    export TA_INCLUDE_PATH="$(brew --prefix ta-lib)/include"
    export TA_LIBRARY_PATH="$(brew --prefix ta-lib)/lib"
    python3.9 -m pip install --no-cache-dir ta-lib
    
    # 3. 验证是否安装成功
    python -c "import talib; print(talib.__version__)"
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
运行结果查看 logs 目录下生成的日志文件 格式为 `logs/sequoia-$YEAR-$MONTH-$DAY-$HOUR-$MINUTE-$SECOND.log`
如：`logs/sequoia-2023-03-03-20-47-56.log`

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

