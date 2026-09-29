# A1 实验报告

## 一、环境搭建和工具安装

- 操作系统与内核：Windows 主机上的 WSL2；实验发行版为 Ubuntu 24.04 LTS（Noble Numbat），内核为 `6.18.33.2-microsoft-standard-WSL2`，架构为 `x86_64`。
- GCC 与 Clang：GCC `13.3.0`；Ubuntu Clang `18.1.3`。
- Python 与 Java：Python `3.12.3`；OpenJDK `17.0.20`。
- Valgrind 与 Linux perf：Valgrind `3.22.0`；`perf version 6.8.12`。
- OpenCilk：已安装 OpenCilk `3.0`；`opencilk-clang --version` 显示 Clang `19.1.7`。以上版本为本机 Ubuntu 环境实测，并非 Windows 原生命令版本。

## 二、常用工具命令操作练习

### （1）`uname -a`

**运行截图**

![题目 1：uname -a 的运行截图](A1/实验截图/1.png)

**作答**

- 输出依次给出内核名称、主机名、内核发行号、构建版本与时间、机器硬件架构、处理器架构、平台架构和操作系统名称；`-a` 表示尽可能列出全部信息。
- 本机内核发行号为 `6.18.33.2-microsoft-standard-WSL2`，机器架构为 `x86_64`，即 x86-64 指令集架构。`Ubuntu 24.04 LTS` 是发行版名称，不是内核版本。

### （2）`cat /etc/os-release`

**运行截图**

![题目 2：cat /etc/os-release 的运行截图](A1/实验截图/2.png)

**作答**

- 该文件以 `键=值` 形式标识 Linux 发行版。截图中的 `NAME=Ubuntu`、`PRETTY_NAME="Ubuntu 24.04 LTS"`、`VERSION_ID="24.04"`、`VERSION_CODENAME=noble` 分别表示名称、展示名称、版本号和代号；`ID=ubuntu`、`ID_LIKE=debian` 说明发行版身份及所属系谱。`HOME_URL`、`SUPPORT_URL`、`BUG_REPORT_URL` 等为项目、支持和报错入口。它不报告内核发行号。

### （3）`sysctl -a`

**运行截图**

![题目 3：sysctl -a 的运行截图](A1/实验截图/3.png)

**作答**

- `sysctl` 读取或设置内核运行时参数；`-a` 列出当前可读取的全部参数。截图中的权限报错表示个别条目受限制，不影响其余参数的读取。
- 这些参数主要映射到 `/proc/sys`：如 `kernel.perf_event_paranoid` 对应 `/proc/sys/kernel/perf_event_paranoid`。点号代替目录分隔符；并非所有目录内容都一定可由当前用户读取。
- 实测 `kernel.ostype = Linux`、`kernel.osrelease = 6.18.33.2-microsoft-standard-WSL2`，分别对应 `uname` 的内核名称和 `uname -r` 的发行号；第（2）题的 `Ubuntu 24.04 LTS` 则是运行在该 Linux 内核上的发行版。
- 实测 `kernel.perf_event_paranoid = 2`：限制普通用户使用 `perf_event` 访问内核等性能事件，数值越高通常越严格；`kernel.perf_event_max_sample_rate = 100000`：性能事件采样频率的内核上限，单位为每秒采样数。这两个值是当前配置，可能随系统设置变化。

### （4）`lscpu`

**运行截图**

![题目 4：lscpu 的运行截图](A1/实验截图/4.png)

**作答**

- `lscpu` 显示处理器为 AMD Ryzen 9 7940HX with Radeon Graphics；1 个插槽、每插槽 16 核、每核 2 线程，因此为 16 个物理核、32 个逻辑 CPU。WSL2 所见缓存为 L1d `512 KiB`（16×32 KiB）、L1i `512 KiB`（16×32 KiB）、L2 `16 MiB`（16×1 MiB）、L3 `32 MiB`（1 组）。这反映虚拟机提供的拓扑；[AMD 官方规格](https://www.amd.com/en/products/processors/laptop/ryzen/7000-series/amd-ryzen-9-7940hx.html)标称 L3 为 64 MB，不能把两个视图混为一谈。`lscpu` 在本机没有给出频率；官方标称基准频率为 **2.4 GHz**、最高加速频率 **5.2 GHz**，未给出可确认的最低频率，不能从当前 1.984 GHz 的瞬时读数推定最低频率。
- 本机为 Little Endian（小端序），多字节数值的低有效字节存于低地址。另一种是 Big Endian（大端序），网络协议规定的 network byte order 是常见应用场景；传输时需进行字节序转换。
- `48 bits physical` 指本环境暴露的物理地址宽度，`48 bits virtual` 指 CPU 实际使用的虚拟地址宽度。`x86_64` 的“64 位”主要表示 64 位指令集和寄存器/指针环境，不意味着全部 64 位都可作为当前有效地址；可用地址宽度由处理器、内核及虚拟化配置决定。

### （5）`dmidecode`

**运行截图**

![题目 5：dmidecode 的运行截图](A1/实验截图/5.png)

**作答**

- `dmidecode` 解码 BIOS/UEFI 提供的 SMBIOS/DMI 硬件表，可查看主板、处理器、内存插槽及模块等信息，通常需要管理员权限。
- 在原生且提供 SMBIOS 的 Linux 系统中，内存条的 `Memory Device` 条目可给出插槽位置、容量、类型、厂商、部件号/序列号、标称速度和配置速度等。**本机 WSL2 无法读取 SMBIOS/DMI**：截图中的 `/dev/mem` 读取失败以及管理员运行时的 `No SMBIOS nor DMI entry point found`，都不能据此填造内存条信息。宿主 Windows 可用 `Get-CimInstance Win32_PhysicalMemory` 另行查询，但这不是 `dmidecode` 的输出。

### （6）`numactl -H` 与 `numactl --show`

**运行截图**

![题目 6：numactl -H 的运行截图](A1/实验截图/6.png)

`numactl --show` 本机文字输出：

```text
policy: default
preferred node: current
physcpubind: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
cpubind: 0
nodebind: 0
membind: 0
preferred:
```

**作答**

- `numactl` 可查看 NUMA 拓扑，并为进程指定 CPU 亲和性、内存绑定或分配策略；`-H`/`--hardware` 展示系统可用的 NUMA 节点、每节点 CPU、内存容量和节点间距离。
- 截图及本机命令均显示 **1 个节点（node 0）**，包含逻辑 CPU 0–31，节点大小约 7539 MB。
- `node distances` 是内核提供的相对访存距离，不是纳秒；本机只有 `0→0 = 10`，所以没有远端节点可比较。多节点机器上，跨节点访问代价可能更高，内存密集型计算、数据库和线程绑定策略会受影响。
- `--show` 显示**当前进程**的 NUMA 策略与允许绑定范围：`policy: default` 表示默认内存策略；`preferred node: current` 表示随当前执行位置选择；`physcpubind: 0…31` 表示可用逻辑 CPU；`cpubind/nodebind/membind: 0` 表示当前只涉及 node 0。它回答“这个进程被如何约束”，`-H` 回答“机器有什么拓扑”。

### （7）`free -h`

**运行截图**

![题目 7：free -h 的运行截图](A1/实验截图/7.png)

**作答**

- `Mem:` 是内存的 `total`、`used`、`free`、`shared`、`buff/cache` 和 `available`；其中 `available` 包含可回收缓存，比单看 `free` 更适合估计还能启动程序的内存。截图中总量约 `7.4 GiB`，这是分配给 WSL2 的可见内存，不等于宿主机物理内存。`Swap:` 是交换空间的总量、已用量和剩余量；截图中总量 `2.0 GiB`、使用量约 0。数值会随负载实时变化。
- `GiB` 是二进制吉比字节，1 GiB = 2³⁰ B；`GB` 是十进制吉字节，1 GB = 10⁹ B。1 GiB 约为 1.074 GB，不能把两个单位的数字直接当成相同容量。

### （8）`ps -aux`

**运行截图**

![题目 8：ps -aux 的运行截图](A1/实验截图/8.png)

**作答**

- `USER`：所有者；`PID`：进程号；`%CPU`：进程 CPU 使用比例（`ps` 的累计平均口径）；`%MEM`：驻留内存占可见物理内存比例；`VSZ`：虚拟地址空间大小（KiB）；`RSS`：驻留物理内存（KiB）；`TTY`：关联终端，`?` 表示无终端；`STAT`：进程状态及附加标志（如 `R` 运行、`S` 睡眠、`Z` 僵尸）；`START`：启动时间；`TIME`：累计 CPU 时间；`COMMAND`：命令及参数。更明确的 BSD 风格写法是 `ps aux`，而 `ps -aux` 在某些实现中可能产生选项歧义。

### （9）`top` 与 `htop`

**运行截图**

`top`：

![题目 9.1：top 的运行截图](A1/实验截图/9.1.png)

`htop`：

![题目 9.2：htop 的运行截图](A1/实验截图/9.2.png)

**作答**

- 顶部依次是当前时间、运行时长、用户数与 1/5/15 分钟负载，任务总数及运行/睡眠/停止/僵尸数，CPU 的用户态 `us`、内核态 `sy`、空闲 `id`、I/O 等待 `wa` 等比例，以及物理内存和交换空间统计。进程表通常包含 `PID`、`USER`、优先级 `PR`、nice 值 `NI`、虚拟内存 `VIRT`、常驻内存 `RES`、共享内存 `SHR`、状态 `S`、`%CPU`、`%MEM`、累计 CPU 时间 `TIME+` 和命令 `COMMAND`；界面可配置，列可能略有不同。
- 二者都实时监视进程和资源；`htop` 默认提供彩色、每逻辑 CPU 的条形图、鼠标/方向键操作、进程树、搜索与排序等更直观的交互。`top` 更基础、通常预装，适合通用终端与脚本化批处理（如 `top -b`）。

### （10）`vmstat 1`

**运行截图**

![题目 10：vmstat 1 的运行截图](A1/实验截图/10.png)

**作答**

- `vmstat` 汇总系统级的进程、内存、交换、块设备 I/O、系统事件和 CPU 状态：`r/b` 是可运行/不可中断睡眠进程数；`swpd/free/buff/cache` 是交换与内存量；`si/so` 是换入/换出；`bi/bo` 是块设备读入/写出；`in/cs` 是中断/上下文切换；`us/sy/id/wa/st` 等是 CPU 时间占比。`vmstat 1` 每秒更新一次；无 `count` 时持续运行。

### （11）`mpstat -P ALL 1`

**运行截图**

![题目 11：mpstat -P ALL 1 的运行截图](A1/实验截图/11.png)

**作答**

- `mpstat -P ALL 1` 每秒报告一次整体 `all` 及每个逻辑 CPU 的使用情况；`-P ALL` 表示列出所有 CPU。`%usr`、`%sys`、`%iowait`、`%irq`、`%soft`、`%steal`、`%idle` 分别反映用户态、内核态、等待 I/O、硬/软中断、被虚拟机管理器占用、空闲等时间比例。它适合观察负载是否集中在少数核心。

### （12）`pidstat 1`

**运行截图**

![题目 12：pidstat 1 的运行截图](A1/实验截图/12.png)

**作答**

- `pidstat 1` 以一秒为间隔显示活跃进程的资源使用，默认视图主要是每进程 CPU 统计。截图所见列包括 `UID`、`PID`、`%usr`（用户态）、`%system`（内核态）、`%guest`（虚拟客户机）、`%wait`（等待 CPU）、`%CPU`（合计）、`CPU`（运行过的逻辑 CPU）和 `Command`。加 `-r`、`-d` 等可查看内存、I/O。它比 `mpstat` 更适合找出具体是哪一个进程在消耗资源。

### （13）`iostat -xz 1`

**运行截图**

![题目 13：iostat -xz 1 的运行截图](A1/实验截图/13.png)

**作答**

- `iostat -xz 1` 每秒报告 CPU 概况与活动磁盘的扩展 I/O 统计：`-x` 开启扩展指标，`-z` 省略采样期间无活动的设备。磁盘列中的 `r/s`、`w/s` 是每秒读写请求，`rkB/s`、`wkB/s` 是吞吐量，`r_await/w_await` 是平均请求等待时间，`aqu-sz` 是平均队列长度，`%util` 是设备忙碌时间比例；新版本还列出丢弃/flush 请求及大小。

**第（10）至（13）题的综合作答**

- 四条命令末尾的 `1` 均表示**采样/刷新间隔 1 秒**，不是只输出 1 条；要限定次数需再给 `count`（如 `vmstat 1 3`）。`vmstat`、`iostat` 的首组数据通常是自启动以来的平均值，后续组才是各一秒区间的值，解释截图时须区分。
- `vmstat` 看系统总体进程队列、内存、换页、I/O 和 CPU；`mpstat` 看整体及逐 CPU 的时间分配；`pidstat` 看逐进程消耗；`iostat` 看块设备吞吐、排队与延迟。四者的统计对象分别是系统、CPU、进程、磁盘，不能把同名百分比直接等同。
- `ps -aux` 的 `%CPU` 主要是进程从启动至读取时的**累计 CPU 时间/运行时间**，不是一秒瞬时值；`pidstat 1` 的 `%CPU` 是最近采样区间内的进程占用；`top`/`htop` 也是按刷新区间估算的近期值，但刷新间隔和显示规范可配置。进程多线程时可能超过单核的 100%；而 `mpstat` 每个 CPU 的各状态百分比以该逻辑 CPU 的时间为分母。比较时须统一时间窗口及“单核还是整机”口径。

### （14）`sar -n DEV 1`

**运行截图**

![题目 14：sar -n DEV 1 的运行截图](A1/实验截图/14.png)

**作答**

- `1` 表示每隔 1 秒重新采样并输出；不加采样次数时持续运行。
- `-n DEV` 选择网络设备层面的统计，逐接口列出接收/发送数据包速率 `rxpck/s`、`txpck/s`，收发字节吞吐 `rxkB/s`、`txkB/s`，压缩包速率 `rxcmp/s`、`txcmp/s`，接收组播 `rxmcst/s`，以及接口利用率估计 `%ifutil`。它反映接口流量，不直接说明某个进程的网络使用量。

### （15）`uptime`

**运行截图**

![题目 15：uptime 的运行截图](A1/实验截图/15.png)

**作答**

- 截图显示当前时间 `14:28:38`、系统已运行 `38 min`、登录用户数 `1 user`，以及负载平均值 `0.01, 0.04, 0.08`。这些是截图时刻的值；再次运行会变化。
- `load average` 依次是最近 **1、5、15 分钟**的平均系统负载，近似反映可运行进程与不可中断等待进程的数量，不是 CPU 使用率百分比。对本机可见的 32 个逻辑 CPU 而言，截图中的数值远低于并行处理容量，说明当时负载很轻。

### （16）`cat /proc/interrupts` 与 `cat /proc/softirqs`


```text
/proc/interrupts: HVS 751941, CAL 679176, HYP 47935, IRQ 25 20026
/proc/softirqs:  SCHED 332274, RCU 199645, TASKLET 52667, TIMER 39238
另一次约 3.1 秒采样增量：HVS +2299、CAL +886、IRQ 25 +34；SCHED +1918、RCU +1111
```

**作答**

- `/proc/interrupts` 按中断源/IRQ 列出每个逻辑 CPU 自启动以来收到的中断次数，以及控制器、触发方式与设备名；其中也有 `HVS`、`CAL` 等虚拟化或处理器间中断。`/proc/softirqs` 按 `TIMER`、`NET_RX`、`SCHED`、`RCU` 等软中断类别列出各 CPU 的累计处理次数。二者都是**累计计数**，若严格比较“频率”应按固定间隔读两次、求计数差再除以间隔，而不是只看单次累计值。
- 本次累计值与约 3.1 秒复测增量中最多的都是 `HVS`（Hyper-V 虚拟定时器中断），与 WSL2 的虚拟化计时有关；`CAL` 是处理器间函数调用中断，也很多。若“硬中断”专指**有编号的设备 IRQ**，最多的是 IRQ 25 `virtio0-virtqueues`，可能与虚拟设备队列的 I/O 活动有关。软中断最多为 `SCHED`，与调度器处理、负载均衡等工作有关；这是根据名称与计数作的原因推断，不等同于逐事件追踪结论。

### （17）`lstopo --of svg > topo.svg`

**运行截图**

![题目 17：生成 topo.svg 的命令截图](A1/实验截图/17.png)

拓扑图（本机重新运行 `lstopo` 生成）：

![本机 CPU 与 NUMA 拓扑](A1/实验截图/topo.svg)

**作答**

- 图中由外到内为 `Machine → Package → NUMANode → L3 → L2/L1/ Core → PU`：1 个处理器包、1 个 NUMA 节点、1 组可见的 32 MiB L3、16 组各 1 MiB L2 和各 32 KiB 的 L1 数据/指令缓存、16 个核心，每核心有 2 个处理单元（PU），合计 32 个逻辑 CPU。图中还列出虚拟网络接口、PCI 桥和磁盘设备。该图反映 **WSL2 客户机可见拓扑**，不保证等同于宿主机的完整物理拓扑。

### （18）Git 命令

**作答**

- 配置提交作者身份可运行 `git config --global user.name "你的姓名"` 和 `git config --global user.email "你的邮箱"`；去掉 `--global` 则只配置当前仓库。本机全局已设置这两项，可用 `git config --global --list` 核对。
- 本机 Git `2.43.0` 未设置 `init.defaultBranch`；此时 `git init` 的初始分支默认是 `master`（首次提交前属于尚未指向提交的分支）。`git config --global init.defaultBranch main` 会使**以后新建**的仓库默认用 `main`，也可在初始化时用 `git init -b main`；已有仓库的当前分支用 `git branch -m main` 改名。应以 `git branch --show-current` 核实实际名称。[Git 官方说明](https://git-scm.com/docs/git-init)
- `git commit` 是否成功取决于是否有暂存的变更及作者身份。仅 `git init` 后直接运行，通常因 `nothing to commit` 而不能产生提交；先 `git add <文件>`，再 `git commit -m "说明"`。若出现 `Author identity unknown`，先按上条设置 `user.name`、`user.email` 后重试。本机身份已配置，但不代表无暂存变更时可提交。
- 示例流程（`demo.png` 仅作演示，**不要忽略报告实际引用的截图**）：先 `git add demo.png`，再 `git commit -m "docs: add demo image"`。若后来不希望继续跟踪，在 `.gitignore` 中新增一行 `demo.png`；由于 `.gitignore` 不会自动移除已跟踪文件，还需 `git rm --cached demo.png`、`git add .gitignore`、`git commit -m "chore: stop tracking demo image"`。`--cached` 只从 Git 索引取消跟踪，保留工作区文件。[Git 官方说明](https://git-scm.com/docs/git-rm)
- 语义化提交用形如 `type(scope): description` 的消息表达变更意图，例如 `feat: add parser`、`fix: handle empty input`、`docs: update report`。其中 `feat` 常对应新功能、`fix` 对应修复；不兼容变更可用 `!` 或 `BREAKING CHANGE:` 标记。这样便于查阅历史、生成变更日志和推断版本号；不是 Git 强制语法。[Conventional Commits 1.0.0 规范](https://www.conventionalcommits.org/en/v1.0.0/)
- `git merge main` 把 `main` 的历史合入当前分支；若无法快进，通常形成合并提交，保留原有分叉历史。`git rebase main` 则把当前分支的提交依次重放到 `main` 之后，使历史更线性，但会改写这些提交的 ID；已共享给他人的分支不应随意 rebase 后强推。两者都可能遇到冲突，需解决后继续操作。

## 三、MIT 6.172 Getting Started

以下依照本地 [A1 Getting Started.pdf](A1/A1%20Getting%20Started.pdf) 的 Write-up 2–8 作答。实验在 WSL2 Ubuntu 24.04 上进行；改动保存在 `A1/solutions`，`A1/code` 下的原始材料未修改。
### Write-up 2：`pointer.c` 中的问题

**作答**

`main(int argc, char *argv[])` 中，`argv` 的形参类型在函数入口处调整为 `char **`，即“指向字符指针的指针”。`pi = &i` 保存整数 `i` 的地址，`j = *pi` 将该地址中的值 5 复制给 `j`。`c` 是可写的字符数组 `"6.172"`；在 `pc = c` 处数组退化为首元素地址，所以 `d = *pc` 得到字符 `'6'`，实测输出 `char d = 6`。`pcp = argv` 合法，因为两者都是 `char **`。

`const char *pcc` 与 `char const *pcc2` 完全等价：指针可重新指向别处，但不能通过它修改所指字符。`char *const cp` 相反：指针本身不能重新赋值，但所指字符可修改。`const char *const cpc` 则两者都不可改。

| 语句                          | 合法性 | 原因                                                     |
| ----------------------------- | ------ | -------------------------------------------------------- |
| `*pcc = '7'`                  | 不合法 | `*pcc` 被视为 `const char`，不能通过 `pcc` 写入。        |
| `pcc = *pcp`                  | 合法   | `*pcp` 是 `char *`，可赋给可重新绑定的 `const char *`。  |
| `pcc = argv[0]`               | 合法   | `argv[0]` 是 `char *`，同上。                            |
| `cp = *pcp`                   | 不合法 | `cp` 是常量指针，初始化后不能改地址。                    |
| `cp = *argv`                  | 不合法 | `*argv` 等于 `argv[0]`，但 `cp` 仍不能重新赋值。         |
| `*cp = '!'`                   | 合法   | `cp` 所指的是可写数组 `c` 的字符；变的是字符，不是指针。 |
| `cpc = *pcp`、`cpc = argv[0]` | 不合法 | `cpc` 本身是常量指针，不能重新绑定。                     |
| `*cpc = '@'`                  | 不合法 | `cpc` 所指字符也带 `const`。                             |

在[解题副本 `pointer.c`](A1/solutions/c-primer/pointer.c) 中注释掉上述不合法赋值后，`make pointer` 编译成功；剩余的未使用变量警告不影响本题判断。

### Write-up 3：类型及其指针的大小

**程序输出**

执行 `make sizes && ./sizes`，本机实测输出如下（单位：字节）：

```text
size of int : 4 bytes
size of short : 2 bytes
size of long : 8 bytes
size of char : 1 bytes
size of float : 4 bytes
size of double : 8 bytes
size of unsigned int : 4 bytes
size of long long : 8 bytes
size of uint8_t : 1 bytes
size of uint16_t : 2 bytes
size of uint32_t : 4 bytes
size of uint64_t : 8 bytes
size of uint_fast8_t : 1 bytes
size of uint_fast16_t : 8 bytes
size of uintmax_t : 8 bytes
size of intmax_t : 8 bytes
size of __int128 : 16 bytes
size of int* : 8 bytes
size of short* : 8 bytes
size of long* : 8 bytes
size of char* : 8 bytes
size of float* : 8 bytes
size of double* : 8 bytes
size of unsigned int* : 8 bytes
size of long long* : 8 bytes
size of uint8_t* : 8 bytes
size of uint16_t* : 8 bytes
size of uint32_t* : 8 bytes
size of uint64_t* : 8 bytes
size of uint_fast8_t* : 8 bytes
size of uint_fast16_t* : 8 bytes
size of uintmax_t* : 8 bytes
size of intmax_t* : 8 bytes
size of __int128* : 8 bytes
size of student : 8 bytes
size of student* : 8 bytes
size of x : 20 bytes
size of &x : 8 bytes
size of int[] : 20 bytes
```

**作答**

本环境为 x86-64 Linux 的 LP64 数据模型，所以这里列出的对象指针均为 8 字节，但**对象大小不等于指针大小**。`student` 由两个 4 字节 `int` 组成，为 8 字节；`x` 是 `int x[5]`，数组本体为 20 字节，`&x` 是指向整个数组的指针，为 8 字节，二者类型不同。`uint_fast16_t` 为了“至少 16 位且便于快速运算”在此实现中占 8 字节，并不保证为 2 字节。输出由[解题副本 `sizes.c`](A1/solutions/c-primer/sizes.c) 产生，原版校验脚本经 Python 3 兼容处理后检查结果为 `LGTM`。

### Write-up 4：用指针实现 `swap()`

**修改后的代码及验证结果**

关键代码（完整文件见[解题副本 `swap.c`](A1/solutions/c-primer/swap.c)）：

```c
void swap(int *i, int *j) {
  int temp = *i;
  *i = *j;
  *j = temp;
}

int main() {
  int k = 1;
  int m = 2;
  swap(&k, &m);
  printf("k = %d, m = %d\n", k, m);
  return 0;
}
```

运行 `make swap && ./swap` 输出 `k = 2, m = 1`；在 `A1/solutions/c-primer` 运行 `python3 verifier.py` 的最终结果为 `LGTM`。原脚本使用 Python 2 的 `print` 写法，本机没有 Python 2，因此只在[校验脚本副本](A1/solutions/c-primer/verifier.py)中做了 Python 3 兼容修改。

**作答**

原版 `swap(int i, int j)` 接收的是 `k`、`m` 的值副本，只交换局部变量，调用者仍会打印 `k = 1, m = 2`。改为传入 `&k`、`&m` 后，函数通过 `*i`、`*j` 直接修改调用者的两个整数，因此完成交换。

### Write-up 5：`make clean; make` 的输出

**程序输出**

把 Makefile 的 `CFLAGS_RELEASE` 从 `-O1` 改为 `-O3` 后，在[矩阵乘法解题副本](A1/solutions/matrix-multiply/Makefile)运行 `make clean && make`，构建阶段的输出为：

```text
rm -f testbed.o matrix_multiply.o matrix_multiply .buildmode \
        testbed.gcda matrix_multiply.gcda \
        testbed.gcno matrix_multiply.gcno \
        testbed.c.gcov matrix_multiply.c.gcov fasttime.h.gcov
clang -O3 -DNDEBUG -Wall -std=c99 -D_POSIX_C_SOURCE=200809L -c testbed.c -o testbed.o
clang -O3 -DNDEBUG -Wall -std=c99 -D_POSIX_C_SOURCE=200809L -c matrix_multiply.c -o matrix_multiply.o
clang -o matrix_multiply testbed.o matrix_multiply.o -lrt -flto -fuse-ld=gold
```

**作答**

`make clean` 清除了旧的目标文件、可执行文件和构建模式标记；`make` 随后以 `-O3` 编译两个 `.c` 文件，并链接为 `matrix_multiply`，构建成功。此输出是**修复矩阵维度前**的阶段记录；构建成功并不代表初始程序运行正确，原始 A 为 4×5、B 为 4×4，二者不能相乘。

### Write-up 6：AddressSanitizer 的报错

**程序输出**

先把 A 的维度改为 4×4，使其与 B 相容；在尚未释放 A/B/C 的阶段执行 `make clean && make ASAN=1 && ./matrix_multiply`，运行时诊断的关键输出为：

```text
Setup
Running matrix_multiply_run()...
==1133==ERROR: LeakSanitizer: detected memory leaks
Direct leak of 48 byte(s) in 3 object(s) allocated from:
    #1 ... in make_matrix .../matrix_multiply.c:39:24
Indirect leak of 192 byte(s) in 12 object(s) allocated from:
    #1 ... in make_matrix .../matrix_multiply.c:48:35
Indirect leak of 96 byte(s) in 3 object(s) allocated from:
    #1 ... in make_matrix .../matrix_multiply.c:46:31
SUMMARY: AddressSanitizer: 336 byte(s) leaked in 18 allocation(s).
```

以上是诊断节选，`...` 省略每次运行都会变化的地址、BuildId 和完整路径；编译阶段 `ld.gold` 的符号导出警告与这次泄漏诊断不是同一问题。

**作答**

三个 `matrix` 对象直接泄漏 48 字节，其内部 12 行数据及 3 个行指针数组间接泄漏 192 + 96 字节，合计 **336 字节、18 次分配**。根因是 `testbed.c` 创建 A、B、C 后未调用 `free_matrix`。此时结果矩阵 C 还存在“未初始化就用 `+=`”的独立问题；ASan/LeakSanitizer 报告的是泄漏，未初始化值问题需通过 Valgrind 等工具发现。

### Write-up 7：修复后的矩阵乘法输出

**程序输出**

在[解题副本 `matrix_multiply.c`](A1/solutions/matrix-multiply/matrix_multiply.c) 的内层累加前将 `C->values[i][j]` 置零，重新构建后运行 `./matrix_multiply -p`，标准输出为：

```text
Matrix A:
------------
    3      7      8      1
    7      9      8      3
    1      2      6      7
    9      8      1      9
------------
Matrix B:
------------
    1      3      0      1
    5      5      7      8
    0      1      9      8
------------
---- RESULTS ----
Result:
------------
   47     55    122    130
   79     83    138    164
   74     40     75    114
  130     95     74    144
------------
---- END RESULTS ----
Elapsed execution time: 0.000000 sec
```

**作答**

矩阵维度修正为 A、B、C 均 4×4；例如结果左上角 `3×1 + 7×5 + 8×0 + 1×9 = 47`，与输出一致。`C[i][j] = 0` 保证每个元素从确定的初值开始累加。4×4 规模过小，本次计时打印为 `0.000000 sec`，不能据此判断真实计算耗时或优化收益。

### Write-up 8：Valgrind 无错误的输出

**程序输出**

在[解题副本 `testbed.c`](A1/solutions/matrix-multiply/testbed.c) 的末尾分别调用 `free_matrix(A)`、`free_matrix(B)`、`free_matrix(C)`，重新以 `-O3` 构建，再运行 `valgrind --error-exitcode=99 --leak-check=full ./matrix_multiply -p`。矩阵结果与 Write-up 7 相同，Valgrind 的结尾输出为：

```text
==1085== HEAP SUMMARY:
==1085==     in use at exit: 0 bytes in 0 blocks
==1085==   total heap usage: 19 allocs, 19 frees, 4,432 bytes allocated
==1085==
==1085== All heap blocks were freed -- no leaks are possible
==1085==
==1085== ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 0 from 0)
```

**作答**

退出时仍占用的堆块为 0，分配和释放次数均为 19，`ERROR SUMMARY` 也为 0，说明这次执行路径没有被 Valgrind 检出的内存错误或泄漏。另以 `-pz` 测试两个零矩阵时，结果矩阵 16 个元素均为 0。
