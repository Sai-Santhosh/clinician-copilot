#!/usr/bin/env python3
"""Evaluation runner for AI output quality assessment."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError

from app.services.llm_client import LLMClient
from app.schemas.ai import AiOutputSchema


class EvaluationRunner:
    """Runner for evaluating AI output quality."""

    def __init__(self, dataset_path: str | None = None):
        """Initialize the evaluation runner.
        
        Args:
            dataset_path: Path to evaluation dataset JSON.
        """
        self.dataset_path = dataset_path or str(
            Path(__file__).parent / "dataset.json"
        )
        self.llm_client = LLMClient()
        self.results: list[dict[str, Any]] = []

    def load_dataset(self) -> list[dict[str, Any]]:
        """Load the evaluation dataset.
        
        Returns:
            List of evaluation examples.
        """
        with open(self.dataset_path) as f:
            return json.load(f)

    async def evaluate_single(
        self, example: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate a single example.
        
        Args:
            example: Evaluation example with transcript and expected values.
            
        Returns:
            Evaluation results for this example.
        """
        result = {
            "id": example["id"],
            "transcript_length": len(example["transcript"]),
            "schema_valid": False,
            "citation_coverage": 0.0,
            "hallucination_score": 0.0,
            "key_field_overlap": 0.0,
            "errors": [],
        }

        try:
            # Generate with temperature=0 for determinism
            output, latency_ms = await self.llm_client.generate(
                transcript=example["transcript"],
                temperature=0.0,
                safe_mode=False,
            )
            result["latency_ms"] = latency_ms
            result["schema_valid"] = True

            # Calculate metrics
            result["citation_coverage"] = self._calculate_citation_coverage(output)
            result["hallucination_score"] = self._calculate_hallucination_score(
                output, example["transcript"]
            )
            result["key_field_overlap"] = self._calculate_key_field_overlap(
                output, example.get("expected", {})
            )

        except ValidationError as e:
            result["errors"].append(f"Schema validation failed: {e}")
        except Exception as e:
            result["errors"].append(f"Generation failed: {type(e).__name__}: {e}")

        return result

    def _calculate_citation_coverage(self, output: AiOutputSchema) -> float:
        """Calculate citation coverage rate.
        
        Each major section should have at least one citation.
        
        Args:
            output: Parsed AI output.
            
        Returns:
            Coverage rate 0-1.
        """
        sections_with_citations = 0
        total_sections = 0

        # Check SOAP sections
        for section_name in ["subjective", "objective", "assessment", "plan"]:
            total_sections += 1
            section = getattr(output.soap, section_name)
            if section.citations:
                sections_with_citations += 1

        # Check diagnosis
        total_sections += 1
        if output.diagnosis.primary and output.diagnosis.primary.citations:
            sections_with_citations += 1
        elif output.diagnosis.differential:
            for dx in output.diagnosis.differential:
                if dx.citations:
                    sections_with_citations += 1
                    break

        # Check medications
        total_sections += 1
        for med in output.medications.medications:
            if med.citations:
                sections_with_citations += 1
                break

        # Check safety plan
        total_sections += 1
        safety_has_citation = False
        for field in ["warning_signs", "coping_strategies", "support_contacts"]:
            items = getattr(output.safety_plan, field)
            for item in items:
                if item.citations:
                    safety_has_citation = True
                    break
            if safety_has_citation:
                break
        if safety_has_citation:
            sections_with_citations += 1

        return sections_with_citations / total_sections if total_sections > 0 else 0.0

    def _calculate_hallucination_score(
        self, output: AiOutputSchema, transcript: str
    ) -> float:
        """Calculate hallucination proxy score.
        
        Lower is better. Checks if key claims appear in transcript.
        
        Args:
            output: Parsed AI output.
            transcript: Original transcript.
            
        Returns:
            Hallucination rate 0-1.
        """
        transcript_lower = transcript.lower()
        
        # Extract key claims from output
        claims = []
        
        # Get diagnoses
        if output.diagnosis.primary:
            claims.append(output.diagnosis.primary.diagnosis.lower())
        for dx in output.diagnosis.differential:
            claims.append(dx.diagnosis.lower())

        # Get medications
        for med in output.medications.medications:
            claims.append(med.medication.lower())

        if not claims:
            return 0.0

        # Check which claims have support in transcript
        unsupported = 0
        for claim in claims:
            # Split multi-word claims and check for any word presence
            words = claim.split()
            found = any(word in transcript_lower for word in words if len(word) > 3)
            if not found:
                unsupported += 1

        return unsupported / len(claims)

    def _calculate_key_field_overlap(
        self, output: AiOutputSchema, expected: dict[str, Any]
    ) -> float:
        """Calculate overlap with expected key fields.
        
        Args:
            output: Parsed AI output.
            expected: Expected values dictionary.
            
        Returns:
            Overlap score 0-1.
        """
        if not expected:
            return 0.0

        matches = 0
        total_expected = 0

        # Check diagnoses
        expected_dx = expected.get("diagnoses", [])
        if expected_dx:
            total_expected += 1
            output_dx_text = ""
            if output.diagnosis.primary:
                output_dx_text += output.diagnosis.primary.diagnosis.lower()
            for dx in output.diagnosis.differential:
                output_dx_text += " " + dx.diagnosis.lower()
            
            for expected_item in expected_dx:
                if expected_item.lower() in output_dx_text:
                    matches += 1
                    break

        # Check key symptoms in SOAP
        expected_symptoms = expected.get("key_symptoms", [])
        if expected_symptoms:
            total_expected += 1
            soap_text = (
                output.soap.subjective.content.lower()
                + " "
                + output.soap.objective.content.lower()
                + " "
                + output.soap.assessment.content.lower()
            )
            
            symptom_matches = sum(
                1 for s in expected_symptoms if s.lower() in soap_text
            )
            if symptom_matches >= len(expected_symptoms) * 0.5:
                matches += 1

        # Check safety concerns
        expected_safety = expected.get("safety_concerns", [])
        if expected_safety:
            total_expected += 1
            safety_text = ""
            for field in ["warning_signs", "coping_strategies", "support_contacts"]:
                items = getattr(output.safety_plan, field)
                for item in items:
                    safety_text += " " + item.item.lower()
            
            safety_matches = sum(
                1 for s in expected_safety if s.lower() in safety_text
            )
            if safety_matches > 0 or not expected_safety:
                matches += 1

        return matches / total_expected if total_expected > 0 else 0.0

    async def run_evaluation(self) -> dict[str, Any]:
        """Run full evaluation on dataset.
        
        Returns:
            Evaluation report.
        """
        dataset = self.load_dataset()
        print(f"Loaded {len(dataset)} evaluation examples")
        print("-" * 50)

        self.results = []
        
        for i, example in enumerate(dataset):
            print(f"Evaluating {example['id']} ({i+1}/{len(dataset)})...", end=" ")
            result = await self.evaluate_single(example)
            self.results.append(result)
            
            if result["schema_valid"]:
                print(f"✓ (latency: {result.get('latency_ms', 'N/A')}ms)")
            else:
                print(f"✗ {result['errors']}")

        # Calculate aggregate metrics
        report = self._generate_report()
        return report

    def _generate_report(self) -> dict[str, Any]:
        """Generate evaluation report.
        
        Returns:
            Report dictionary.
        """
        valid_results = [r for r in self.results if r["schema_valid"]]
        
        report = {
            "total_examples": len(self.results),
            "schema_validity_rate": len(valid_results) / len(self.results) if self.results else 0,
            "avg_citation_coverage": 0.0,
            "avg_hallucination_score": 0.0,
            "avg_key_field_overlap": 0.0,
            "avg_latency_ms": 0.0,
            "individual_results": self.results,
        }

        if valid_results:
            report["avg_citation_coverage"] = sum(
                r["citation_coverage"] for r in valid_results
            ) / len(valid_results)
            report["avg_hallucination_score"] = sum(
                r["hallucination_score"] for r in valid_results
            ) / len(valid_results)
            report["avg_key_field_overlap"] = sum(
                r["key_field_overlap"] for r in valid_results
            ) / len(valid_results)
            
            latencies = [r.get("latency_ms", 0) for r in valid_results if r.get("latency_ms")]
            if latencies:
                report["avg_latency_ms"] = sum(latencies) / len(latencies)

        return report

    def print_report(self, report: dict[str, Any]) -> None:
        """Print report as formatted table.
        
        Args:
            report: Evaluation report.
        """
        print()
        print("=" * 60)
        print("EVALUATION REPORT")
        print("=" * 60)
        print()
        print(f"Total Examples:        {report['total_examples']}")
        print(f"Schema Validity Rate:  {report['schema_validity_rate']:.1%}")
        print(f"Avg Citation Coverage: {report['avg_citation_coverage']:.1%}")
        print(f"Avg Hallucination:     {report['avg_hallucination_score']:.1%}")
        print(f"Avg Key Field Overlap: {report['avg_key_field_overlap']:.1%}")
        print(f"Avg Latency:           {report['avg_latency_ms']:.0f}ms")
        print()
        print("-" * 60)
        print("INDIVIDUAL RESULTS")
        print("-" * 60)
        print(f"{'ID':<12} {'Valid':<6} {'Citations':<10} {'Halluc.':<10} {'Overlap':<10}")
        print("-" * 60)
        
        for r in report["individual_results"]:
            valid = "✓" if r["schema_valid"] else "✗"
            print(
                f"{r['id']:<12} {valid:<6} "
                f"{r['citation_coverage']:.1%:<10} "
                f"{r['hallucination_score']:.1%:<10} "
                f"{r['key_field_overlap']:.1%:<10}"
            )
        
        print("=" * 60)

    def save_report(self, report: dict[str, Any], output_path: str) -> None:
        """Save report to JSON file.
        
        Args:
            report: Evaluation report.
            output_path: Output file path.
        """
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run AI evaluation")
    parser.add_argument(
        "--dataset", 
        default=None,
        help="Path to evaluation dataset JSON"
    )
    parser.add_argument(
        "--output", 
        default="eval_report.json",
        help="Output path for JSON report"
    )
    args = parser.parse_args()

    runner = EvaluationRunner(dataset_path=args.dataset)
    
    try:
        report = await runner.run_evaluation()
        runner.print_report(report)
        runner.save_report(report, args.output)
    except Exception as e:
        print(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
