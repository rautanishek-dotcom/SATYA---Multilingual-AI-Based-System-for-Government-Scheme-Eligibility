import os
import time
import json
import logging
from typing import Dict, Any, List
from collections import defaultdict
from vault.ocr_engine import OCREngine
from vault.field_extractor import FieldExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BenchmarkEngine:
    """
    Phase 12: Benchmarking Harness.
    Evaluates OCR classification and extraction accuracy against ground truth data.
    """
    
    def __init__(self, dataset_dir: str, ground_truth_json: str):
        self.dataset_dir = dataset_dir
        self.ground_truth = {}
        if os.path.exists(ground_truth_json):
            with open(ground_truth_json, "r") as f:
                self.ground_truth = json.load(f)
                
        self.metrics = {
            "total_documents": 0,
            "classification_correct": 0,
            "field_metrics": defaultdict(lambda: {"correct": 0, "total": 0}),
            "total_processing_time_ms": 0
        }
        self.confusion_matrix = defaultdict(lambda: defaultdict(int))

    def run_benchmark(self):
        logger.info("Starting SATYA Enterprise OCR Benchmark")
        
        for root, _, files in os.walk(self.dataset_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                    img_path = os.path.join(root, file)
                    doc_id = os.path.splitext(file)[0]
                    
                    if doc_id not in self.ground_truth:
                        logger.warning(f"No ground truth for {doc_id}, skipping.")
                        continue
                        
                    gt = self.ground_truth[doc_id]
                    self.metrics["total_documents"] += 1
                    
                    t0 = time.time()
                    
                    # 1. OCR Extraction
                    ocr_res = OCREngine.extract(img_path)
                    
                    # 2. Layout and Extraction
                    extraction = FieldExtractor.extract_fields(ocr_res)
                    
                    processing_time = int((time.time() - t0) * 1000)
                    self.metrics["total_processing_time_ms"] += processing_time
                    
                    predicted_type = extraction["document_type"]
                    actual_type = gt.get("document_type", "unknown")
                    
                    self.confusion_matrix[actual_type][predicted_type] += 1
                    
                    if predicted_type == actual_type:
                        self.metrics["classification_correct"] += 1
                        
                    for field, expected_val in gt.get("fields", {}).items():
                        self.metrics["field_metrics"][field]["total"] += 1
                        predicted_val = extraction["fields"].get(field, {}).get("value", "")
                        
                        # Soft match for names, hard match for numbers
                        if field == "document_number" and expected_val.replace(" ", "") == predicted_val.replace(" ", ""):
                            self.metrics["field_metrics"][field]["correct"] += 1
                        elif field != "document_number" and expected_val.lower() in predicted_val.lower():
                            self.metrics["field_metrics"][field]["correct"] += 1

        self._generate_report()

    def _generate_report(self):
        total = self.metrics["total_documents"]
        if total == 0:
            logger.error("No documents benchmarked.")
            return
            
        print("\n" + "="*50)
        print("SATYA OCR BENCHMARK REPORT")
        print("="*50)
        print(f"Total Documents Processed: {total}")
        
        avg_time = self.metrics["total_processing_time_ms"] / total
        print(f"Average Processing Time:   {avg_time:.2f} ms / doc")
        
        class_acc = (self.metrics["classification_correct"] / total) * 100
        print(f"Classification Accuracy:   {class_acc:.2f}%")
        
        print("\n--- Field Level Accuracy ---")
        for field, stats in self.metrics["field_metrics"].items():
            if stats["total"] > 0:
                acc = (stats["correct"] / stats["total"]) * 100
                print(f"{field.capitalize().ljust(20)}: {acc:.2f}%")
                
        print("\n--- Confusion Matrix ---")
        for actual, predictions in self.confusion_matrix.items():
            for pred, count in predictions.items():
                print(f"Actual: {actual.ljust(15)} -> Predicted: {pred.ljust(15)} | Count: {count}")

if __name__ == "__main__":
    # Example usage
    runner = BenchmarkEngine(dataset_dir="uploads/benchmark_data", ground_truth_json="uploads/benchmark_truth.json")
    # runner.run_benchmark()
