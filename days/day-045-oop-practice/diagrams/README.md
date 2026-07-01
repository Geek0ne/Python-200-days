# Day 045 - 图解

## ORM 框架类结构

```mermaid
classDiagram
    class Field {
        +bool primary_key
        +Any value
        +validate(value) Any
    }

    class CharField {
        +int max_length
        +validate(value) str
    }

    class IntegerField {
        +validate(value) int
    }

    class FloatField {
        +validate(value) float
    }

    class BooleanField {
        +validate(value) bool
    }

    class ForeignKey {
        +Type related_model
        +validate(value) int
    }

    class ModelMeta {
        +__new__(name, bases, attrs)
    }

    class Model {
        +int id
        +Dict _fields
        +str _table_name
        +save() bool
        +get(id) Model
        +filter(**kwargs) list
        +all() list
    }

    class User {
        +CharField name
        +IntegerField age
        +CharField email
    }

    class Article {
        +CharField title
        +CharField content
        +IntegerField author_id
        +BooleanField published
    }

    Field <|-- CharField
    Field <|-- IntegerField
    Field <|-- FloatField
    Field <|-- BooleanField
    Field <|-- ForeignKey

    ModelMeta ..> Model : creates
    Model <|-- User
    Model <|-- Article

    User "1" --> "*" Article : has
```

## REST API 客户端结构

```mermaid
classDiagram
    class APIClient {
        +str base_url
        +str api_key
        +Dict session_headers
        +_build_url(endpoint) str
        +_simulate_request(method, url) dict
        +get(endpoint, params) Any
        +post(endpoint, data) Any
        +put(endpoint, data) Any
        +delete(endpoint) bool
    }

    class UserAPI {
        +get_users(page, limit) list
        +get_user(user_id) dict
        +create_user(name, email, age) dict
        +update_user(user_id, **kwargs) dict
        +delete_user(user_id) bool
    }

    class ArticleAPI {
        +get_articles(author_id, page) list
        +get_article(article_id) dict
        +create_article(title, content, author_id) dict
        +update_article(article_id, **kwargs) dict
        +delete_article(article_id) bool
    }

    class CommentAPI {
        +get_comments(article_id) list
        +create_comment(article_id, user_id, content) dict
        +delete_comment(article_id, comment_id) bool
    }

    APIClient <|-- UserAPI
    APIClient <|-- ArticleAPI
    APIClient <|-- CommentAPI

    UserAPI ..> ArticleAPI : creates
    ArticleAPI ..> CommentAPI : has
```

## 学生管理系统结构

```mermaid
classDiagram
    class Person {
        <<abstract>>
        +str name
        +int age
        +datetime created_at
        +get_role()* str
        +get_info()* str
    }

    class Student {
        +str student_id
        +str grade
        +Dict grades
        +List attendance
        +float average_score
        +bool is_passing
        +str grade_level
        +add_grade(subject, score)
        +remove_grade(subject)
        +record_attendance(present)
        +float attendance_rate
    }

    class Teacher {
        +str subject
        +str title
        +List students
        +List teaching_classes
        +int student_count
        +add_student(student)
        +remove_student(student)
        +add_class(class_name)
        +remove_class(class_name)
    }

    class Classroom {
        +str name
        +int max_capacity
        +Teacher teacher
        +List students
        +int student_count
        +bool is_full
        +set_teacher(teacher)
        +add_student(student) bool
        +remove_student(student) bool
        +float get_class_average()
        +float get_passing_rate()
        +List get_top_students(n)
    }

    class School {
        +str name
        +List classrooms
        +List teachers
        +int classroom_count
        +int teacher_count
        +add_classroom(classroom)
        +add_teacher(teacher)
        +float get_school_average()
        +float get_school_passing_rate()
        +dict get_statistics()
    }

    Person <|-- Student
    Person <|-- Teacher
    Classroom "1" --> "0..1" Teacher : has
    Classroom "1" --> "*" Student : contains
    School "1" --> "*" Classroom : contains
    School "1" --> "*" Teacher : employs
```

## ORM 工作流程

```mermaid
flowchart TD
    A[用户定义 Model] --> B[ModelMeta 元类处理]
    B --> C[收集 Field 字段]
    C --> D[生成 _fields 字典]
    D --> E[创建表结构映射]
    E --> F[用户实例化 Model]
    F --> G[设置字段值]
    G --> H[调用 save 方法]
    H --> I[验证字段值]
    I --> J[生成 SQL 语句]
    J --> K[执行数据库操作]

    style A fill:#e1f5fe
    style F fill:#e8f5e8
    style K fill:#fff3e0
```

## REST API 请求流程

```mermaid
flowchart TD
    A[创建 API 客户端] --> B[设置 base_url 和 api_key]
    B --> C[构建完整 URL]
    C --> D{选择 HTTP 方法}
    D -->|GET| E[发送 GET 请求]
    D -->|POST| F[发送 POST 请求]
    D -->|PUT| G[发送 PUT 请求]
    D -->|DELETE| H[发送 DELETE 请求]
    E --> I[处理响应]
    F --> I
    G --> I
    H --> I
    I --> J{请求成功?}
    J -->|是| K[返回结果]
    J -->|否| L[重试机制]
    L --> M{重试次数 < 3?}
    M -->|是| C
    M -->|否| N[抛出异常]

    style A fill:#e1f5fe
    style K fill:#e8f5e8
    style N fill:#ffebee
```

## 面向对象核心概念关系

```mermaid
flowchart LR
    A[面向对象编程] --> B[封装]
    A --> C[继承]
    A --> D[多态]

    B --> B1[私有属性]
    B --> B2[属性装饰器]
    B --> B3[方法封装]

    C --> C1[单继承]
    C --> C2[多继承]
    C --> C3[方法重写]

    D --> D1[方法覆盖]
    D --> D2[接口实现]
    D --> D3[抽象基类]

    B1 --> E[信息隐藏]
    B2 --> E
    C1 --> F[代码复用]
    C2 --> F
    C3 --> F
    D1 --> G[灵活扩展]
    D2 --> G
    D3 --> G

    E --> H[安全性]
    F --> H
    G --> H

    style A fill:#e1f5fe
    style H fill:#e8f5e8
```

---

## 核心设计模式

### 1. 元类模式（ORM 框架）
```
用户代码 → 元类处理 → 类定义 → 实例化 → 使用
```

### 2. 继承模式（API 客户端）
```
基类（通用功能）→ 子类（业务逻辑）→ 使用
```

### 3. 组合模式（学生系统）
```
School → Classroom → Student/Teacher
```

### 4. 装饰器模式（重试机制）
```
函数 → 装饰器包装 → 增强功能 → 调用
```
