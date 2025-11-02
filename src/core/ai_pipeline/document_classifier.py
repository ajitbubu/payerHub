from src.ai_pipeline.document_classifier import DocumentClassifier

classifier = DocumentClassifier()

text = """
Prior Authorization Request
Member ID: ABC123456
...
"""

result = classifier.classify(text)
print(f"Document Type: {result['document_type']}")
print(f"Confidence: {result['confidence']:.2f}")
print(f"Keywords: {result['keywords_found']}")

# With context (filename + metadata)
result = classifier.classify_with_context(
    text=text,
    filename="pa_request_20250115.pdf",
    metadata={'payer': 'bcbs'}
)

# Batch classification
documents = [
    {'text': text1, 'id': 'doc1'},
    {'text': text2, 'id': 'doc2'}
]
results = classifier.batch_classify(documents)