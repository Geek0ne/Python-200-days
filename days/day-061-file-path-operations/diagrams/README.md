# Day 061 — 文件与路径操作 · 图解

## os 模块 vs pathlib 对比

```
操作              os 模块                     pathlib.Path
──────────────────────────────────────────────────────────────
创建路径      os.path.join(a,b,c)       Path(a) / b / c
判断存在      os.path.exists(p)         p.exists()
判断文件      os.path.isfile(p)         p.is_file()
判断目录      os.path.isdir(p)          p.is_dir()
获取大小      os.path.getsize(p)        p.stat().st_size
文件名        os.path.basename(p)       p.name
父目录        os.path.dirname(p)        p.parent
后缀          os.path.splitext(p)[1]    p.suffix
绝对路径      os.path.abspath(p)        p.resolve()
读文件        open(p).read()            p.read_text()
写文件        open(p,'w').write(s)      p.write_text(s)
列目录        os.listdir(d)             list(d.iterdir())
遍历          os.walk(d)                d.rglob("*")
删除文件      os.remove(p)              p.unlink()
创建目录      os.makedirs(p)            p.mkdir(parents=True)
```

## pathlib 路径结构

```
/home/user/documents/report.pdf
│    │    │          │        │
│    │    │          │        └─ .suffix = ".pdf"
│    │    │          ├─ .stem = "report"
│    │    │          └─ .name = "report.pdf"
│    │    └─ .parent = /home/user/documents
│    └─ .parent.parent = /home/user
└─ .root = /

.parts = ('/', 'home', 'user', 'documents', 'report.pdf')
```

## 文件同步流程

```
┌──────────────┐         ┌──────────────┐
│   源目录     │         │   目标目录    │
│  (Source)    │         │  (Dest)      │
├──────────────┤         ├──────────────┤
│ file_a.txt   │ ──比较──│ file_a.txt   │  → 更新（源更新）
│ file_b.txt   │         │ file_b.txt   │  → 未变
│ file_c.txt   │         │ old_file.txt │  → 删除（源无）
│ (new)        │         │              │  → 创建（源有）
└──────────────┘         └──────────────┘
        │                       │
        └─────── 同步 ──────────┘
              │
        ┌─────▼─────┐
        │ 操作报告   │
        │ • 创建 1  │
        │ • 更新 1  │
        │ • 删除 1  │
        │ • 未变 1  │
        └───────────┘
```

## shutil 功能矩阵

```
功能          函数                      说明
──────────────────────────────────────────────────────
复制文件      shutil.copy(src, dst)     复制内容+权限
              shutil.copy2(src, dst)    复制内容+权限+元数据
              shutil.copyfile(src, dst) 仅复制内容
复制目录      shutil.copytree(s, d)     递归复制整个目录树
移动          shutil.move(src, dst)     移动文件/目录
删除目录      shutil.rmtree(path)       递归删除目录树 ⚠️
压缩          shutil.make_archive(...)  创建 zip/tar 压缩包
解压          shutil.unpack_archive(...) 解压压缩包
查找          shutil.which(cmd)         查找可执行文件路径
磁盘          shutil.disk_usage(path)   获取磁盘使用统计
```

## 文件操作安全清单

```
操作前检查                          安全措施
──────────────────────────────────────────────
删除文件前      → 确认路径在允许范围内
                → 用 trash 替代 rm
                → 记录删除日志

写入文件前      → 检查磁盘空间
                → 先写临时文件再 rename
                → 用 with 语句确保关闭

读取文件前      → 检查文件是否存在
                → 处理编码异常
                → 限制读取大小

复制大文件      → 用 shutil.copy2 保留元数据
                → 显示进度条
                → 支持断点续传
```
