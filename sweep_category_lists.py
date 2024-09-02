#!/usr/bin/python3

import os
import apt

# Doğru yolu kontrol edin
os.chdir("/usr/share/linuxmint/mintinstall/categories")

# Paket önbelleğini yükleyin
c = apt.Cache()

# Kategorideki her dosya için işlemleri başlatın
for file in os.listdir():
    new = []
    file_path = os.path.join(os.getcwd(), file)
    with open(file_path, "r") as f:
        for line in f:
            if line.startswith("flatpak:") or line == "\n":
                new.append(line)
            else:
                pkg_name = line.rstrip()
                if pkg_name in c:
                    new.append(line)
                else:
                    print(f"missing {pkg_name}")
    
    # Değişiklikleri yazmak için dosyayı açın
    with open(file_path, "w") as f:
        f.write("".join(new))
