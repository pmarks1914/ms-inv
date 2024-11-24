import tensorflow as tf
import numpy as np
import torch
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForTokenClassification,
    AutoModelForSequenceClassification
)
from sklearn.model_selection import train_test_split
from datetime import datetime
import json
import pandas as pd
from datasets import load_dataset
from transformers import Trainer, TrainingArguments


class InvoiceAutomation:
    def __init__(self, use_gpu=False):
        # Set device
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        # Initialize NLP models with specific versions and device settings
        try:
            # Fine-tuning NER Model if needed (for demonstration)
            ner_model_name = "distilbert-base-uncased"
            self.ner_tokenizer = AutoTokenizer.from_pretrained(ner_model_name)
            self.ner_model = AutoModelForTokenClassification.from_pretrained(ner_model_name)

            # Fine-tune the model (uncomment to train on your own NER dataset)
            # self.fine_tune_ner_model()

            self.ner_model.to(self.device)
            self.nlp = pipeline("ner",
                                model=self.ner_model,
                                tokenizer=self.ner_tokenizer,
                                device=0 if self.device == "cuda" else -1)

            # Text Classification Pipeline
            classifier_model_name = "distilbert-base-uncased-finetuned-sst-2-english"
            self.classifier_tokenizer = AutoTokenizer.from_pretrained(classifier_model_name)
            self.classifier_model = AutoModelForSequenceClassification.from_pretrained(classifier_model_name)
            self.classifier_model.to(self.device)
            self.text_classifier = pipeline("text-classification",
                                           model=self.classifier_model,
                                           tokenizer=self.classifier_tokenizer,
                                           device=0 if self.device == "cuda" else -1)

            print("Models loaded successfully")

        except Exception as e:
            print(f"Error loading models: {str(e)}")
            raise

        # Initialize invoice template structure
        self.invoice_template = {
            "invoiceNumber": "",
            "date": "",
            "companyName": "",
            "companyAddress": "",
            "clientName": "",
            "clientAddress": "",
            "items": [],
            "notes": "",
            "currency": "USD",
        }

    def fine_tune_ner_model(self):
        """Fine-tune the NER model on a custom dataset (e.g., CoNLL-2003)."""
        dataset = load_dataset('conll2003')

        # Initialize model for token classification
        model = AutoModelForTokenClassification.from_pretrained('distilbert-base-uncased', num_labels=9)

        # Define training arguments
        training_args = TrainingArguments(
            output_dir='./results',
            evaluation_strategy="epoch",
            learning_rate=2e-5,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=64,
            num_train_epochs=3,
            weight_decay=0.01,
        )

        # Initialize Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset['train'],
            eval_dataset=dataset['validation'],
        )

        # Train the model
        trainer.train()

    def extract_entities(self, text):
        """Extract relevant entities from text using NLP"""
        try:
            entities = self.nlp(text)
            extracted_info = {
                "company_names": [],
                "addresses": [],
                "amounts": [],
                "dates": []
            }

            current_entity = ""
            current_tokens = []

            for entity in entities:
                if entity['entity'].startswith('B-'):
                    if current_tokens:
                        self._add_entity_to_extracted_info(current_entity, ' '.join(current_tokens), extracted_info)
                    current_tokens = [entity['word']]
                    current_entity = entity['entity'][2:]  # Remove 'B-' prefix
                elif entity['entity'].startswith('I-'):
                    current_tokens.append(entity['word'])

            # Add the last entity if exists
            if current_tokens:
                self._add_entity_to_extracted_info(current_entity, ' '.join(current_tokens), extracted_info)

            return extracted_info

        except Exception as e:
            print(f"Error in entity extraction: {str(e)}")
            return {
                "company_names": [],
                "addresses": [],
                "amounts": [],
                "dates": []
            }

    def _add_entity_to_extracted_info(self, entity_type, text, extracted_info):
        """Helper method to add extracted entities to the appropriate category"""
        if entity_type == 'ORG':
            extracted_info["company_names"].append(text)
        elif entity_type == 'LOC':
            extracted_info["addresses"].append(text)
        elif entity_type == 'MONEY':
            extracted_info["amounts"].append(text)
        elif entity_type == 'DATE':
            extracted_info["dates"].append(text)

    def categorize_items(self, description):
        """Categorize invoice items using text classification"""
        try:
            # Handle potential memory issues with long text
            max_length = 512
            if len(description) > max_length:
                description = description[:max_length]

            category = self.text_classifier(description)[0]
            return category['label']

        except Exception as e:
            print(f"Error in item categorization: {str(e)}")
            return "UNCATEGORIZED"

    def predict_next_invoice_number(self, previous_numbers):
        """Predict next invoice number based on pattern"""
        try:
            if not previous_numbers:
                return "INV-001"

            last_num = max(int(num.split('-')[1]) for num in previous_numbers
                           if num.startswith('INV-') and num.split('-')[1].isdigit())
            return f"INV-{str(last_num + 1).zfill(3)}"

        except Exception as e:
            print(f"Error in invoice number prediction: {str(e)}")
            return "INV-001"

    def calculate_totals(self, items):
        """Calculate invoice totals"""
        try:
            subtotal = sum(float(item['quantity']) * float(item['price'])
                           for item in items if 'quantity' in item and 'price' in item)
            tax_rate = 0.1  # 10% tax rate (configurable)
            tax = subtotal * tax_rate
            total = subtotal + tax

            return {
                "subtotal": round(subtotal, 2),
                "tax": round(tax, 2),
                "total": round(total, 2)
            }

        except Exception as e:
            print(f"Error in total calculation: {str(e)}")
            return {
                "subtotal": 0.00,
                "tax": 0.00,
                "total": 0.00
            }

    def generate_invoice(self, input_data):
        """Generate complete invoice using ML/NLP processing"""
        try:
            # Create new invoice based on template
            invoice = self.invoice_template.copy()

            # Extract and process company/client information
            if 'rawText' in input_data:
                extracted_info = self.extract_entities(input_data['rawText'])
                invoice['companyName'] = extracted_info['company_names'][0] if extracted_info['company_names'] else ""
                invoice['clientName'] = extracted_info['company_names'][1] if len(extracted_info['company_names']) > 1 else ""

            # Set basic invoice details
            invoice['invoiceNumber'] = self.predict_next_invoice_number(input_data.get('previousInvoices', []))
            invoice['date'] = datetime.now().strftime('%Y-%m-%d')

            # Process items
            if 'items' in input_data:
                processed_items = []
                for item in input_data['items']:
                    processed_item = {
                        'description': item.get('description'),
                        'quantity': float(item.get('quantity', 0)),
                        'price': float(item.get('price', 0)),
                        'category': self.categorize_items(item.get('description'))
                    }
                    processed_items.append(processed_item)
                invoice['items'] = processed_items

            # Calculate totals
            totals = self.calculate_totals(invoice['items'])
            invoice.update(totals)

            return invoice

        except Exception as e:
            print(f"Error generating invoice: {str(e)}")
            return None

    def cleanup(self):
        """Clean up resources and free memory"""
        try:
            # Clear CUDA cache if using GPU
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # Delete model attributes
            del self.ner_model
            del self.classifier_model
            del self.nlp
            del self.text_classifier

        except Exception as e:
            print(f"Error during cleanup: {str(e)}")


# Example usage
if __name__ == "__main__":
    try:
        # Initialize automation system with GPU if available
        use_gpu = torch.cuda.is_available()
        invoice_system = InvoiceAutomation(use_gpu=False)  # Change to `True` to use GPU

        # Sample input data
        sample_data = {
            "rawText": "Invoice from Tech Corp (123 Tech St, City) to Client Inc (456 Client Ave, Town)",
            "items": [
                {"description": "Software Development", "quantity": 10, "price": 150.00},
                {"description": "Cloud Hosting", "quantity": 1, "price": 299.99}
            ],
            "previousInvoices": ["INV-001", "INV-002"]
        }

        # Generate invoice
        invoice = invoice_system.generate_invoice(sample_data)
        if invoice:
            print(json.dumps(invoice, indent=2))

        # Clean up resources
        invoice_system.cleanup()

    except Exception as e:
        print(f"Error during execution: {str(e)}")

