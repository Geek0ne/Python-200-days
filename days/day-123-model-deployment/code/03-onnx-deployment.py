#!/usr/bin/env python3
"""
Day 123 - ONNX 模型导出与部署
演示如何将 Scikit-learn / PyTorch 模型转换为 ONNX 格式并部署
"""

import numpy as np
import os
import json
import time
import pickle
from datetime import datetime


# ============================================================
# 1. 训练 Scikit-learn 模型
# ============================================================

def train_sklearn_model():
    """训练一个 Iris 分类模型"""
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    
    print("=" * 60)
    print("1. 训练 Scikit-learn 模型")
    print("=" * 60)
    
    iris = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, random_state=42
    )
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"训练集大小: {X_train.shape[0]}")
    print(f"测试集大小: {X_test.shape[0]}")
    print(f"准确率: {accuracy:.4f}")
    print(f"\n分类报告:")
    print(classification_report(y_test, y_pred, target_names=iris.target_names))
    
    return model, iris


# ============================================================
# 2. 转换为 ONNX 格式
# ============================================================

def convert_to_onnx(model, iris):
    """将 Scikit-learn 模型转换为 ONNX"""
    print("\n" + "=" * 60)
    print("2. 转换为 ONNX 格式")
    print("=" * 60)
    
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
        
        # 定义输入类型
        n_features = iris.data.shape[1]
        initial_type = [('float_input', FloatTensorType([None, n_features]))]
        
        # 转换
        onnx_model = convert_sklearn(
            model, 
            initial_types=initial_type,
            target_opset=13  # 指定 ONNX opset 版本
        )
        
        # 保存
        os.makedirs('models', exist_ok=True)
        onnx_path = 'models/iris_model.onnx'
        with open(onnx_path, 'wb') as f:
            f.write(onnx_model.SerializeToString())
        
        file_size = os.path.getsize(onnx_path)
        print(f"✅ ONNX 模型已保存: {onnx_path}")
        print(f"模型大小: {file_size / 1024:.2f} KB")
        
        return onnx_path
    
    except ImportError:
        print("⚠️  skl2onnx 未安装，跳过 ONNX 转换")
        print("安装命令: pip install skl2onnx")
        return None


# ============================================================
# 3. ONNX Runtime 推理
# ============================================================

def onnx_inference(onnx_path, iris):
    """使用 ONNX Runtime 进行推理"""
    print("\n" + "=" * 60)
    print("3. ONNX Runtime 推理")
    print("=" * 60)
    
    try:
        import onnxruntime as ort
        
        # 加载模型
        session = ort.InferenceSession(onnx_path)
        
        # 获取输入输出信息
        input_info = session.get_inputs()[0]
        output_info = session.get_outputs()[0]
        
        print(f"输入名称: {input_info.name}")
        print(f"输入形状: {input_info.shape}")
        print(f"输入类型: {input_info.type}")
        print(f"输出名称: {output_info.name}")
        print(f"输出形状: {output_info.shape}")
        
        # 测试推理
        test_samples = np.array([
            [5.1, 3.5, 1.4, 0.2],  # setosa
            [6.2, 2.9, 4.3, 1.3],  # versicolor
            [7.7, 3.0, 6.1, 2.3],  # virginica
        ], dtype=np.float32)
        
        print(f"\n推理测试:")
        print(f"{'样本':>8} {'预测类别':>12} {'真实类别':>12} {'正确':>6}")
        print("-" * 45)
        
        for i, sample in enumerate(test_samples):
            start = time.time()
            result = session.run(
                [output_info.name], 
                {input_info.name: sample.reshape(1, -1)}
            )
            inference_time = (time.time() - start) * 1000
            
            pred_class = result[0][0]
            true_class = [0, 1, 2][i]
            correct = "✅" if pred_class == true_class else "❌"
            
            print(f"  {i+1:>6} {iris.target_names[pred_class]:>12} "
                  f"{iris.target_names[true_class]:>12} {correct:>6} "
                  f"({inference_time:.2f}ms)")
        
        # 性能测试
        print(f"\n性能测试 (1000次推理):")
        dummy_input = test_samples[0].reshape(1, -1)
        
        # 预热
        for _ in range(100):
            session.run([output_info.name], {input_info.name: dummy_input})
        
        # 正式测试
        start = time.time()
        for _ in range(1000):
            session.run([output_info.name], {input_info.name: dummy_input})
        total_time = (time.time() - start) * 1000
        
        print(f"  总耗时: {total_time:.2f} ms")
        print(f"  平均耗时: {total_time/1000:.4f} ms/次")
        print(f"  QPS: {1000/(total_time/1000):.0f}")
        
        return session
    
    except ImportError:
        print("⚠️  onnxruntime 未安装，跳过 ONNX 推理")
        print("安装命令: pip install onnxruntime")
        return None


# ============================================================
# 4. Pickle vs ONNX 性能对比
# ============================================================

def compare_formats(model, onnx_path, iris):
    """对比 Pickle 和 ONNX 的推理性能"""
    print("\n" + "=" * 60)
    print("4. Pickle vs ONNX 性能对比")
    print("=" * 60)
    
    test_input = np.array([[5.1, 3.5, 1.4, 0.2]], dtype=np.float32)
    n_runs = 1000
    
    # Pickle 推理
    start = time.time()
    for _ in range(n_runs):
        model.predict(test_input)
    pickle_time = (time.time() - start) * 1000
    
    results = {
        "Pickle": {
            "avg_time_ms": pickle_time / n_runs,
            "qps": n_runs / (pickle_time / 1000),
        }
    }
    
    print(f"\n{'格式':>10} {'平均耗时(ms)':>14} {'QPS':>10}")
    print("-" * 40)
    print(f"{'Pickle':>10} {results['Pickle']['avg_time_ms']:>14.4f} "
          f"{results['Pickle']['qps']:>10.0f}")
    
    # ONNX 推理
    if onnx_path and os.path.exists(onnx_path):
        try:
            import onnxruntime as ort
            
            session = ort.InferenceSession(onnx_path)
            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name
            
            # 预热
            for _ in range(100):
                session.run([output_name], {input_name: test_input})
            
            start = time.time()
            for _ in range(n_runs):
                session.run([output_name], {input_name: test_input})
            onnx_time = (time.time() - start) * 1000
            
            results["ONNX"] = {
                "avg_time_ms": onnx_time / n_runs,
                "qps": n_runs / (onnx_time / 1000),
            }
            
            print(f"{'ONNX':>10} {results['ONNX']['avg_time_ms']:>14.4f} "
                  f"{results['ONNX']['qps']:>10.0f}")
            
            # 对比
            speedup = pickle_time / onnx_time
            print(f"\n🚀 ONNX 比 Pickle 快 {speedup:.2f}x")
        
        except ImportError:
            pass
    
    return results


# ============================================================
# 5. 模型元数据
# ============================================================

def save_metadata(model, iris, results):
    """保存模型元数据"""
    print("\n" + "=" * 60)
    print("5. 保存模型元数据")
    print("=" * 60)
    
    metadata = {
        "model_name": "Iris 分类器",
        "algorithm": "RandomForest",
        "framework": "scikit-learn",
        "features": list(iris.feature_names),
        "classes": iris.target_names.tolist(),
        "n_features": int(iris.data.shape[1]),
        "n_classes": len(iris.target_names),
        "training_samples": 120,
        "created_at": datetime.now().isoformat(),
        "formats": {
            "pickle": "models/iris_model.pkl",
            "onnx": "models/iris_model.onnx",
        },
        "performance": {
            format_name: {
                "avg_inference_ms": round(info["avg_time_ms"], 4),
                "qps": round(info["qps"], 0),
            }
            for format_name, info in results.items()
        },
    }
    
    with open('models/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 元数据已保存: models/metadata.json")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


# ============================================================
# 6. 主函数
# ============================================================

def main():
    print("=" * 60)
    print("🔄 ONNX 模型导出与部署演示")
    print("=" * 60)
    
    # 1. 训练模型
    model, iris = train_sklearn_model()
    
    # 保存 Pickle 模型
    os.makedirs('models', exist_ok=True)
    with open('models/iris_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    print(f"✅ Pickle 模型已保存: models/iris_model.pkl")
    
    # 2. 转换为 ONNX
    onnx_path = convert_to_onnx(model, iris)
    
    # 3. ONNX 推理
    if onnx_path:
        onnx_inference(onnx_path, iris)
    
    # 4. 性能对比
    results = compare_formats(model, onnx_path, iris)
    
    # 5. 保存元数据
    save_metadata(model, iris, results)
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ ONNX 模型导出与部署演示完成！")
    print("=" * 60)
    print("""
核心要点:
1. ONNX 是跨框架的开放模型格式
2. skl2onnx 可将 Scikit-learn 模型转为 ONNX
3. ONNX Runtime 提供高性能 C++ 推理引擎
4. ONNX 通常比 Pickle 推理更快
5. ONNX 支持多语言部署 (Python/C++/Java/Go)
6. 生产环境推荐使用 ONNX 格式
""")


if __name__ == "__main__":
    main()
