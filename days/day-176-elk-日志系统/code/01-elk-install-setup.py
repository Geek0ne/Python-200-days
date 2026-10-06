#!/usr/bin/env python3
"""
Day 176 — ELK 日志系统
一键部署单节点 ELK（docker-compose）
"""

import subprocess
import sys
import time
import urllib.request
import json

ELK_STACK_YAML = """
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    container_name: elk-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    networks:
      - elk-net

  logstash:
    image: docker.elastic.co/logstash/logstash:8.15.0
    container_name: elk-logstash
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch
    networks:
      - elk-net

  kibana:
    image: docker.elastic.co/kibana/kibana:8.15.0
    container_name: elk-kibana
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    networks:
      - elk-net

volumes:
  es-data:

networks:
  elk-net:
"""

LOGSTASH_CONF = """
input {
  file {
    path => "/var/log/nginx/access.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
  }
}

filter {
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
  date {
    match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+yyyy.MM.dd}"
  }
  stdout { codec => rubydebug }
}
"""

def run(cmd, check=True):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"ERROR: {r.stderr}")
        sys.exit(1)
    return r

def health_check(retries=30, interval=2):
    for i in range(retries):
        try:
            with urllib.request.urlopen("http://localhost:9200/_cluster/health", timeout=5) as resp:
                data = json.loads(resp.read())
                status = data.get("status", "unknown")
                print(f"ES health: {status}")
                if status in ("green", "yellow"):
                    return True
        except Exception as e:
            print(f"  waiting... ({e})")
        time.sleep(interval)
    return False

def main():
    print("=" * 60)
    print("Day 176 — ELK 日志系统 · 一键部署")
    print("=" * 60)

    # 1. 写 docker-compose.yml
    with open("elk-stack.yml", "w") as f:
        f.write(ELK_STACK_YAML)
    print("✅ elk-stack.yml 已写")

    # 2. 写 logstash.conf
    with open("logstash.conf", "w") as f:
        f.write(LOGSTASH_CONF)
    print("✅ logstash.conf 已写")

    # 3. 启动
    run("docker-compose -f elk-stack.yml up -d")

    # 4. 健康检查
    if health_check():
        print("🎉 ELK 部署成功！")
        print("   Kibana: http://localhost:5601")
        print("   ES:      http://localhost:9200")
    else:
        print("❌ ES 健康检查超时")
        sys.exit(1)

if __name__ == "__main__":
    main()
