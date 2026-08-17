#!/usr/bin/env python3
"""
Gym Locker System - HTTP API Tester
This script simulates multiple users checking in/out and verifies locker assignment.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional


class GymTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.check_in_endpoint = f"{base_url}/api/gate/check-in"
        self.check_out_endpoint = f"{base_url}/api/gate/check-out"
        self.results = []
        
    def test_check_in(self, national_id: str) -> Dict:
        """Test user check-in via API"""
        try:
            response = requests.post(
                self.check_in_endpoint,
                json={"national_id": national_id},
                timeout=5
            )
            result = {
                "timestamp": datetime.now().isoformat(),
                "action": "check_in",
                "national_id": national_id,
                "status_code": response.status_code,
                "success": False,
                "locker_number": None,
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                result["success"] = data.get("success", False)
                result["locker_number"] = data.get("assigned_locker")
                result["locker_opened"] = data.get("locker_opened", False)
                result["message"] = data.get("message")
            else:
                data = response.json()
                result["error"] = data.get("error", response.text)
            
            self.results.append(result)
            return result
        except Exception as e:
            result = {
                "timestamp": datetime.now().isoformat(),
                "action": "check_in",
                "national_id": national_id,
                "status_code": None,
                "success": False,
                "error": str(e)
            }
            self.results.append(result)
            return result
    
    def test_check_out(self, national_id: str) -> Dict:
        """Test user check-out via API"""
        try:
            response = requests.post(
                self.check_out_endpoint,
                json={"national_id": national_id},
                timeout=5
            )
            result = {
                "timestamp": datetime.now().isoformat(),
                "action": "check_out",
                "national_id": national_id,
                "status_code": response.status_code,
                "success": False,
                "points_earned": 0,
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                result["success"] = data.get("success", False)
                result["points_earned"] = data.get("points_earned", 0)
                result["message"] = data.get("message")
            else:
                data = response.json()
                result["error"] = data.get("error", response.text)
            
            self.results.append(result)
            return result
        except Exception as e:
            result = {
                "timestamp": datetime.now().isoformat(),
                "action": "check_out",
                "national_id": national_id,
                "status_code": None,
                "success": False,
                "error": str(e)
            }
            self.results.append(result)
            return result
    
    def print_result(self, result: Dict):
        """Pretty print a result"""
        if result["action"] == "check_in":
            status = "✓ SUCCESS" if result["success"] else "✗ FAILED"
            print(f"\n[CHECK-IN] {status}")
            print(f"  National ID: {result['national_id']}")
            print(f"  HTTP Status: {result['status_code']}")
            if result["success"]:
                print(f"  🔑 Assigned Locker: {result['locker_number']}")
                led_status = "🟢 ON" if result.get("locker_opened") else "🔴 OFF"
                print(f"  💡 LED Status: {led_status}")
                if result.get("message"):
                    print(f"  📝 {result['message']}")
            else:
                print(f"  ❌ Error: {result['error']}")
        
        elif result["action"] == "check_out":
            status = "✓ SUCCESS" if result["success"] else "✗ FAILED"
            print(f"\n[CHECK-OUT] {status}")
            print(f"  National ID: {result['national_id']}")
            print(f"  HTTP Status: {result['status_code']}")
            if result["success"]:
                print(f"  ⭐ Points Earned: {result['points_earned']}")
                if result.get("message"):
                    print(f"  📝 {result['message']}")
            else:
                print(f"  ❌ Error: {result['error']}")
    
    def run_test_scenario(self):
        """Run a complete test scenario"""
        print("=" * 60)
        print("🏋️ Smart Gym Locker System - API Test")
        print("=" * 60)
        print(f"Testing against: {self.base_url}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test users from seed_data.py
        test_users = [
            ("1111111111", "امیرحسین محمدی"),
            ("2222222222", "علیرضا کریمی"),
            ("3333333333", "محمد جواد اکبری"),
        ]
        
        print("\n" + "=" * 60)
        print("Test 1: Multiple Users Check-In (Assign 3 Lockers)")
        print("=" * 60)
        
        assigned_lockers = {}
        for nid, name in test_users:
            print(f"\n👤 Testing user: {name} (ID: {nid})")
            result = self.test_check_in(nid)
            self.print_result(result)
            if result["success"]:
                assigned_lockers[nid] = result["locker_number"]
        
        print("\n" + "-" * 60)
        print("Summary of Assigned Lockers:")
        for nid, locker in assigned_lockers.items():
            print(f"  User {nid}: Locker #{locker}")
        
        # Verify all 3 lockers are different
        if len(set(assigned_lockers.values())) == 3:
            print("✓ All 3 users assigned to different lockers!")
        else:
            print("⚠️  Warning: Not all users assigned to different lockers")
        
        print("\n" + "=" * 60)
        print("Test 2: Check-Out and Verify Cleanup")
        print("=" * 60)
        
        # Wait a bit to simulate time in gym
        print("\n⏳ Simulating 2 seconds of gym time...\n")
        time.sleep(2)
        
        for nid, name in test_users[:2]:  # Check out first 2 users
            print(f"\n👤 Checking out user: {name} (ID: {nid})")
            result = self.test_check_out(nid)
            self.print_result(result)
        
        print("\n" + "=" * 60)
        print("Test 3: Verify Locker Re-assignment (Check-In Again)")
        print("=" * 60)
        
        print(f"\n👤 First user (ID: 1111111111) checks in again...")
        result = self.test_check_in("1111111111")
        self.print_result(result)
        if result["success"]:
            old_locker = assigned_lockers.get("1111111111")
            new_locker = result["locker_number"]
            if old_locker != new_locker:
                print(f"✓ New locker assignment: {old_locker} → {new_locker}")
            else:
                print(f"⚠️  Same locker reassigned: {new_locker}")
        
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        check_ins = [r for r in self.results if r["action"] == "check_in"]
        check_outs = [r for r in self.results if r["action"] == "check_out"]
        
        successful_ins = sum(1 for r in check_ins if r["success"])
        successful_outs = sum(1 for r in check_outs if r["success"])
        
        print(f"Total Check-ins: {len(check_ins)} | Successful: {successful_ins}")
        print(f"Total Check-outs: {len(check_outs)} | Successful: {successful_outs}")
        print(f"\nTest Results:")
        print(f"  ✓ Total operations: {len(self.results)}")
        print(f"  ✓ Successful operations: {sum(1 for r in self.results if r.get('success', False))}")
        print(f"  ✗ Failed operations: {sum(1 for r in self.results if not r.get('success', False))}")
        
        print("\n" + "=" * 60)
        print("🎯 Test completed!")
        print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test Smart Gym Locker System API"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="Base URL of the gym API (default: http://localhost:5000)"
    )
    
    args = parser.parse_args()
    
    tester = GymTester(base_url=args.url)
    
    try:
        tester.run_test_scenario()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")


if __name__ == "__main__":
    main()
