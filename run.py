import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from spotifyProject.main import main
except ImportError as e:
    print(f"[SpotiTool] Failed to import app — is spotifyProject in the right place?\n  {e}")
    input("Press Enter to exit...")
    sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print("\n[SpotiTool] An unexpected error occurred:\n")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
