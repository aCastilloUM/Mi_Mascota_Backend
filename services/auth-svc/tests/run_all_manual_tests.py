"""
Ejecutar todos los tests manuales en secuencia
"""
import subprocess
import sys
import os
import time
import json

TESTS = [
    ("1_register", "Registro de usuario"),
    ("2_login", "Login y obtención de tokens"),
    ("3_me", "Acceso a /me con access token"),
    ("4_refresh", "Refresh token"),
    ("5_logout", "Logout"),
]

def run_test(test_file, description):
    print("\n" + "="*80)
    print(f"EJECUTANDO: {description}")
    print("="*80)
    
    result = subprocess.run(
        [sys.executable, f"manual_test_{test_file}.py"],
        capture_output=False,
        cwd=os.path.dirname(__file__) or "."
    )
    
    return result.returncode == 0

def main():
    print("="*80)
    print("SUITE DE TESTS MANUALES - REFRESH TOKEN Y LOGOUT")
    print("="*80)
    print("\nEste script ejecutará todos los tests en secuencia")
    print("Asegúrate de que el servicio esté corriendo en http://localhost:8000")
    
    input("\nPresiona ENTER para comenzar...")
    
    results = []
    
    for test_file, description in TESTS:
        success = run_test(test_file, description)
        results.append((description, success))
        
        if not success and test_file == "1_register":
            print("\n⚠️  El registro falló, pero puede ser que el usuario ya exista.")
            print("   Continuando con los siguientes tests...")
        
        time.sleep(1)  # Pausa entre tests
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE TESTS")
    print("="*80)
    
    for description, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {description}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nResultado: {passed}/{total} tests completados exitosamente")
    
    if passed == total:
        print("\n🎉 TODOS LOS TESTS PASARON 🎉")
    else:
        print(f"\n⚠️  {total - passed} test(s) tuvieron problemas")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests interrumpidos por el usuario")
    except Exception as e:
        print(f"\n\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
