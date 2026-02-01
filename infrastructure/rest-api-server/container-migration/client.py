#!/usr/bin/env python3
"""
Container Migration Client
Uses the serverless MCP API to complete Phase 2 and Phase 3
"""

import requests
import json
import os
import subprocess
from pathlib import Path

class ContainerMigrationClient:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip('/')
        
    def optimize_dockerfile(self, app_path: str, base_image: str = "node:18-alpine", port: int = 3000):
        """Generate optimized Dockerfile"""
        response = requests.post(
            f"{self.api_url}/tools/optimize_dockerfile",
            json={
                "base_image": base_image,
                "port": port
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            dockerfile_path = Path(app_path) / "Dockerfile"
            dockerfile_path.write_text(result['dockerfile'])
            print(f"✅ {result['message']}")
            print(f"📄 Dockerfile created at: {dockerfile_path}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    def build_and_push_container(self, app_name: str, tag: str = "v1.0.0", region: str = "us-west-2"):
        """Get build commands for ECR"""
        response = requests.post(
            f"{self.api_url}/tools/build_and_push_container",
            json={
                "app_name": app_name,
                "tag": tag,
                "region": region
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            print(f"🏷️  Image URI: {result['image_uri']}")
            print("\n📋 Run these commands:")
            for cmd in result['build_commands']:
                print(f"   {cmd}")
            return result['image_uri'], result['build_commands']
        else:
            print(f"❌ Error: {response.text}")
            return None, None
    
    def validate_container_security(self, dockerfile_path: str):
        """Validate container security"""
        try:
            with open(dockerfile_path, 'r') as f:
                dockerfile_content = f.read()
        except FileNotFoundError:
            print(f"❌ Dockerfile not found at {dockerfile_path}")
            return False
            
        response = requests.post(
            f"{self.api_url}/tools/validate_container_security",
            json={"dockerfile_content": dockerfile_content}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("🔒 Container Security Validation")
            print(f"📊 Security Score: {result['security_score']:.1f}%")
            
            if result['recommendations']:
                print("\n✅ Strengths:")
                for rec in result['recommendations']:
                    print(f"   {rec}")
            
            if result['issues']:
                print("\n⚠️  Issues to address:")
                for issue in result['issues']:
                    print(f"   {issue}")
            
            return result['security_score'] > 80
        else:
            print(f"❌ Error: {response.text}")
            return False
    
    def get_dockerfile_template(self):
        """Get Dockerfile template"""
        response = requests.get(f"{self.api_url}/resources/dockerfile-template")
        
        if response.status_code == 200:
            result = response.json()
            return result['template']
        else:
            print(f"❌ Error: {response.text}")
            return None
    
    def get_build_script(self):
        """Get build script"""
        response = requests.get(f"{self.api_url}/resources/build-script")
        
        if response.status_code == 200:
            result = response.json()
            return result['script']
        else:
            print(f"❌ Error: {response.text}")
            return None

def complete_phase_2_and_3(api_url: str, app_path: str, app_name: str):
    """Complete Phase 2 (Containerization) and Phase 3 (ECR Push)"""
    
    client = ContainerMigrationClient(api_url)
    
    print("🚀 Starting Phase 2: Containerization")
    print("=" * 50)
    
    # Step 1: Optimize Dockerfile
    print("\n📝 Step 1: Optimizing Dockerfile...")
    if not client.optimize_dockerfile(app_path):
        return False
    
    # Step 2: Validate Security
    print("\n🔒 Step 2: Validating Security...")
    dockerfile_path = Path(app_path) / "Dockerfile"
    if not client.validate_container_security(str(dockerfile_path)):
        print("⚠️  Security validation failed, but continuing...")
    
    print("\n🚀 Starting Phase 3: ECR Push")
    print("=" * 50)
    
    # Step 3: Get build commands
    print("\n📦 Step 3: Preparing ECR build...")
    image_uri, build_commands = client.build_and_push_container(app_name)
    
    if not image_uri:
        return False
    
    # Step 4: Execute build commands
    print("\n🔨 Step 4: Building and pushing container...")
    print("💡 You can run these commands manually, or we can execute them now.")
    
    choice = input("Execute build commands now? (y/N): ").lower().strip()
    
    if choice == 'y':
        try:
            original_dir = os.getcwd()
            os.chdir(app_path)
            
            for cmd in build_commands:
                print(f"🔄 Executing: {cmd}")
                # Parse command string into list for safe execution
                import shlex
                # Security: shlex.split() safely parses command string
                cmd_list = shlex.split(cmd)
                # Security: shlex.split() safely parses command string without shell injection risk
                result = subprocess.run(cmd_list, check=True, capture_output=True, text=True)
                if result.stdout:
                    print(result.stdout)
            
            os.chdir(original_dir)
            print(f"✅ Container successfully pushed to: {image_uri}")
            return image_uri
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            print(f"Error output: {e.stderr}")
            os.chdir(original_dir)
            return False
    else:
        print("📋 Manual execution required. Run the commands shown above.")
        return image_uri

if __name__ == "__main__":
    # Configuration
    API_URL = input("Enter the API Gateway URL: ").strip()
    APP_PATH = "$PROJECT_ROOT/sample-app"
    APP_NAME = "secure-blog"
    
    if not API_URL:
        print("❌ API URL is required")
        exit(1)
    
    # Execute Phase 2 and 3
    result = complete_phase_2_and_3(API_URL, APP_PATH, APP_NAME)
    
    if result:
        print("\n🎉 Phase 2 and 3 completed successfully!")
        print(f"📦 Container image: {result}")
        print("\n🔄 Next: Deploy to ECS Express Mode")
    else:
        print("\n❌ Phase 2/3 failed. Check the errors above.")
