#!/usr/bin/env python3
"""
Test Suite for Serverless Container Migration MCP Server
Tests all API endpoints and validates responses
"""

import requests
import json
import time
import sys

class MCPServerTester:
    def __init__(self, api_url):
        self.api_url = api_url.rstrip('/')
        self.test_results = []
    
    def test_dockerfile_template(self):
        """Test GET /resources/dockerfile-template"""
        print("🧪 Testing Dockerfile Template...")
        
        try:
            response = requests.get(f"{self.api_url}/resources/dockerfile-template")
            
            if response.status_code == 200:
                data = response.json()
                if 'template' in data and 'FROM node:18-alpine' in data['template']:
                    print("✅ Dockerfile template endpoint working")
                    return True
                else:
                    print("❌ Invalid template content")
                    return False
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def test_build_script(self):
        """Test GET /resources/build-script"""
        print("🧪 Testing Build Script...")
        
        try:
            response = requests.get(f"{self.api_url}/resources/build-script")
            
            if response.status_code == 200:
                data = response.json()
                if 'script' in data and 'docker build' in data['script']:
                    print("✅ Build script endpoint working")
                    return True
                else:
                    print("❌ Invalid script content")
                    return False
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def test_optimize_dockerfile(self):
        """Test POST /tools/optimize_dockerfile"""
        print("🧪 Testing Dockerfile Optimization...")
        
        try:
            payload = {
                "base_image": "node:18-alpine",
                "port": 3000
            }
            
            response = requests.post(
                f"{self.api_url}/tools/optimize_dockerfile",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'dockerfile' in data and 'USER nodejs' in data['dockerfile']:
                    print("✅ Dockerfile optimization working")
                    return True
                else:
                    print("❌ Invalid dockerfile content")
                    return False
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def test_validate_security(self):
        """Test POST /tools/validate_container_security"""
        print("🧪 Testing Security Validation...")
        
        try:
            dockerfile_content = """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY src/ ./src/
USER nodejs
HEALTHCHECK CMD curl -f http://localhost:3000/health
CMD ["npm", "start"]"""
            
            payload = {
                "dockerfile_content": dockerfile_content
            }
            
            response = requests.post(
                f"{self.api_url}/tools/validate_container_security",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'security_score' in data and data['security_score'] > 0:
                    print(f"✅ Security validation working (Score: {data['security_score']}%)")
                    return True
                else:
                    print("❌ Invalid security response")
                    return False
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def test_build_and_push(self):
        """Test POST /tools/build_and_push_container"""
        print("🧪 Testing Build and Push...")
        
        try:
            payload = {
                "app_name": "test-app",
                "tag": "test-v1.0.0",
                "region": "us-west-2"
            }
            
            response = requests.post(
                f"{self.api_url}/tools/build_and_push_container",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'image_uri' in data and 'build_commands' in data:
                    print("✅ Build and push endpoint working")
                    return True
                else:
                    print("❌ Invalid build response")
                    return False
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def test_performance(self):
        """Test API response times"""
        print("🧪 Testing Performance...")
        
        try:
            start_time = time.time()
            response = requests.get(f"{self.api_url}/resources/dockerfile-template")
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200 and response_time < 5000:  # 5 second threshold
                print(f"✅ Performance test passed ({response_time:.0f}ms)")
                return True
            else:
                print(f"❌ Performance test failed ({response_time:.0f}ms)")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests and return summary"""
        print("🚀 Starting MCP Server API Tests")
        print("=" * 50)
        
        tests = [
            ("Dockerfile Template", self.test_dockerfile_template),
            ("Build Script", self.test_build_script),
            ("Dockerfile Optimization", self.test_optimize_dockerfile),
            ("Security Validation", self.test_validate_security),
            ("Build and Push", self.test_build_and_push),
            ("Performance", self.test_performance)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            if test_func():
                passed += 1
                self.test_results.append((test_name, "PASS"))
            else:
                self.test_results.append((test_name, "FAIL"))
        
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        for test_name, result in self.test_results:
            status = "✅" if result == "PASS" else "❌"
            print(f"{status} {test_name}: {result}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tests passed! MCP Server is working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Check the API deployment.")
            return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 test_mcp_server.py <API_URL>")
        print("Example: python3 test_mcp_server.py https://8vrpbef7gc.execute-api.us-west-2.amazonaws.com/Prod")
        sys.exit(1)
    
    api_url = sys.argv[1]
    tester = MCPServerTester(api_url)
    
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
