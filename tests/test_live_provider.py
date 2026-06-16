"""Quick live test of the ASPXProvider against the real GTU site.

Run with:
    python tests/test_live_provider.py

This is NOT a pytest test - it requires network access to gtu.ac.in.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gtu_academic_engine.provider.aspx_provider import ASPXProvider, STATIC_COURSES

if __name__ == "__main__":
    print("=" * 60)
    print("GTU ASPXProvider Live Test")
    print("=" * 60)

    with ASPXProvider(headless=False) as provider:  # headless=False so you can see it
        print("\n[1] Courses (static):", len(STATIC_COURSES))
        for c in STATIC_COURSES[:3]:
            print("   ", c["id"], "-", c["name"])
        print("   ...")

        print("\n[2] Fetching branches for BE...")
        branches = provider.fetch_branches("BE")
        print("   Found:", len(branches), "branches")
        for b in branches[:5]:
            print("   ", b["id"], "-", b["name"])
        if len(branches) > 5:
            print("   ...")

        if branches:
            bid = branches[0]["id"]
            print(f"\n[3] Fetching semesters for BE/{bid}...")
            sems = provider.fetch_semesters("BE", bid)
            print("   Found:", len(sems), "semesters:", [s["value"] for s in sems])

            if sems:
                sem_val = sems[0]["value"]
                print(f"\n[4] Fetching electives for BE/{bid}/sem={sem_val}...")
                electives = provider.fetch_elective_types("BE", bid, sem_val)
                print("   Found:", electives)

                if electives:
                    print(f"\n[5] Fetching subjects for BE/{bid}/sem={sem_val}/{electives[0]}...")
                    subjects = provider.fetch_subjects("BE", bid, sem_val, electives[0])
                    print("   Found:", len(subjects), "subjects")
                    for s in subjects[:5]:
                        print("   ", s["subject_code"], "-", s["subject_name"])

    print("\nDone!")

