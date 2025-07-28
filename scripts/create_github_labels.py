#!/usr/bin/env python3
"""
Script to create GitHub labels for SAGE development
Run this before creating issues
"""

import subprocess
import sys
from typing import List, Dict

class GitHubLabelCreator:
    """Creates GitHub labels for SAGE development"""
    
    def __init__(self, repo: str = "MarinDushku/SAGE"):
        self.repo = repo
        self.labels = self._define_labels()
        
    def _define_labels(self) -> List[Dict]:
        """Define all GitHub labels with colors and descriptions"""
        return [
            # Priority Labels
            {
                "name": "priority:high",
                "color": "d73a4a",
                "description": "Critical for core functionality"
            },
            {
                "name": "priority:medium", 
                "color": "fbca04",
                "description": "Important but not blocking"
            },
            {
                "name": "priority:low",
                "color": "0e8a16",
                "description": "Nice to have features"
            },
            
            # Component Labels
            {
                "name": "core",
                "color": "1d76db",
                "description": "Core infrastructure components"
            },
            {
                "name": "module:voice",
                "color": "8B5CF6",
                "description": "Voice processing module"
            },
            {
                "name": "module:nlp",
                "color": "10B981",
                "description": "Natural language processing module"
            },
            {
                "name": "module:vision",
                "color": "F59E0B",
                "description": "Computer vision module"
            },
            {
                "name": "module:calendar",
                "color": "EF4444",
                "description": "Calendar and scheduling module"
            },
            {
                "name": "module:web",
                "color": "3B82F6",
                "description": "Web integration module"
            },
            {
                "name": "module:integration",
                "color": "6366F1",
                "description": "System integration module"
            },
            {
                "name": "module:learning",
                "color": "EC4899",
                "description": "Adaptive learning module"
            },
            {
                "name": "module:fabrication",
                "color": "84CC16",
                "description": "3D printing and fabrication module"
            },
            
            # Optimization Labels
            {
                "name": "optimization:cpu",
                "color": "FF6B6B",
                "description": "CPU performance improvements"
            },
            {
                "name": "optimization:memory",
                "color": "4ECDC4",
                "description": "Memory usage optimization"
            },
            {
                "name": "optimization:quality",
                "color": "45B7D1",
                "description": "Quality improvements"
            },
            {
                "name": "optimization:speed",
                "color": "96CEB4",
                "description": "Speed and latency improvements"
            },
            
            # Cost and Technology Labels
            {
                "name": "cost:free",
                "color": "28a745",
                "description": "Uses only free technologies"
            },
            {
                "name": "cost:paid",
                "color": "dc3545",
                "description": "Requires paid services"
            },
            {
                "name": "tech:ai",
                "color": "6f42c1",
                "description": "AI and machine learning related"
            },
            {
                "name": "tech:audio",
                "color": "fd7e14",
                "description": "Audio processing related"
            },
            {
                "name": "tech:web",
                "color": "20c997",
                "description": "Web technologies"
            },
            
            # Status Labels
            {
                "name": "status:completed",
                "color": "0e8a16",
                "description": "Fully implemented and tested"
            },
            {
                "name": "status:in-progress",
                "color": "fbca04",
                "description": "Currently being worked on"
            },
            {
                "name": "status:blocked",
                "color": "b60205",
                "description": "Waiting for dependencies"
            },
            {
                "name": "status:needs-testing",
                "color": "5319e7",
                "description": "Implementation done, needs testing"
            },
            {
                "name": "status:needs-review",
                "color": "0052cc",
                "description": "Ready for code review"
            },
            
            # Type Labels
            {
                "name": "type:feature",
                "color": "a2eeef",
                "description": "New feature or enhancement"
            },
            {
                "name": "type:bug",
                "color": "d73a4a",
                "description": "Bug fix"
            },
            {
                "name": "type:documentation",
                "color": "0075ca",
                "description": "Documentation improvements"
            },
            {
                "name": "type:refactor",
                "color": "cfd3d7",
                "description": "Code refactoring"
            },
            {
                "name": "type:test",
                "color": "bfdadc",
                "description": "Testing related"
            },
            
            # Difficulty Labels
            {
                "name": "difficulty:easy",
                "color": "c5f5c5",
                "description": "Good for beginners"
            },
            {
                "name": "difficulty:medium",
                "color": "fef2c0",
                "description": "Moderate complexity"
            },
            {
                "name": "difficulty:hard",
                "color": "f8d7da",
                "description": "High complexity"
            },
            
            # Special Labels
            {
                "name": "good first issue",
                "color": "7057ff",
                "description": "Good for newcomers"
            },
            {
                "name": "help wanted",
                "color": "008672",
                "description": "Community help requested"
            },
            {
                "name": "milestone:week1",
                "color": "ededed",
                "description": "Core Infrastructure milestone"
            },
            {
                "name": "milestone:week2-3",
                "color": "ededed", 
                "description": "Voice Module milestone"
            },
            {
                "name": "milestone:week4-5",
                "color": "ededed",
                "description": "Local AI Integration milestone"
            }
        ]
    
    def create_label(self, label: Dict) -> bool:
        """Create a single GitHub label"""
        try:
            cmd = [
                "gh", "label", "create",
                label["name"],
                "--color", label["color"],
                "--description", label["description"]
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Created label: {label['name']}")
            return True
            
        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr:
                print(f"⚠️  Label already exists: {label['name']}")
                return True
            else:
                print(f"❌ Failed to create label '{label['name']}': {e}")
                print(f"Error output: {e.stderr}")
                return False
                
    def create_all_labels(self) -> None:
        """Create all GitHub labels"""
        print("🏷️  Creating GitHub labels for SAGE development...")
        print(f"Repository: {self.repo}")
        print(f"Total labels to create: {len(self.labels)}")
        print()
        
        success_count = 0
        
        for i, label in enumerate(self.labels, 1):
            print(f"Creating label {i}/{len(self.labels)}: {label['name']}")
            if self.create_label(label):
                success_count += 1
                
        print()
        print(f"✅ Successfully created/verified {success_count}/{len(self.labels)} labels")
        
        if success_count < len(self.labels):
            print("⚠️  Some labels failed to create. Check the error messages above.")
        else:
            print("🎉 All labels are ready! You can now create issues with proper labeling.")


def main():
    """Main function"""
    creator = GitHubLabelCreator()
    
    # Check if GitHub CLI is available
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ GitHub CLI not found or not authenticated")
        print("Please install GitHub CLI and authenticate first:")
        print("1. Install: https://cli.github.com/")
        print("2. Authenticate: gh auth login")
        return 1
        
    creator.create_all_labels()
    return 0


if __name__ == "__main__":
    exit(main())