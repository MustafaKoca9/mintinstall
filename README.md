# Mintinstall

**Mintinstall**, Linux Mint için resmi Yazılım Yöneticisi uygulamasıdır. Bu uygulama, kullanıcıların yazılımları kolayca bulmasını, yüklemesini ve yönetmesini sağlar. Mintinstall, kullanıcı dostu arayüzü ve geniş yazılım yelpazesi ile Linux Mint topluluğu tarafından geniş çapta tercih edilmektedir.

![Mintinstall Ekran Görüntüsü](https://user-images.githubusercontent.com/19881231/122644976-86767180-d120-11eb-9cf4-eed2813f749b.png)

## Özellikler

- **Kullanıcı Dostu Arayüz**: Mintinstall, sade ve anlaşılır arayüzü ile tüm kullanıcı seviyelerine hitap eder.
- **Geniş Yazılım Yelpazesi**: Farklı kategorilerde binlerce uygulamaya erişim sağlayın.

- **Detaylı Uygulama Bilgileri**: Uygulamalar hakkında yorumlar, değerlendirmeler ve ekran görüntüleri ile detaylı bilgi alın.

## Kurulum

### Kaynak Kodunu İndirin

Mintinstall'u kendi makinenizde derlemek için aşağıdaki adımları izleyin:

```bash
git clone https://github.com/linuxmint/mintinstall
cd mintinstall
```

### Derleme

Projenin bağımlılıklarını yükledikten sonra, `dpkg-buildpackage` komutunu kullanarak Mintinstall'u derleyebilirsiniz:

```bash
dpkg-buildpackage --no-sign
```

### Kurulum

Derleme tamamlandıktan sonra, aşağıdaki komutla Mintinstall'u sisteminize kurabilirsiniz:

```bash
cd ..
sudo dpkg -i mintinstall*.deb
```

## Katkıda Bulunun

### Çeviriler

Mintinstall'un çevirilerine katkıda bulunmak için Launchpad platformunu kullanabilirsiniz. Bu platform, çevirilerin topluluk tarafından düzenlenmesine olanak sağlar. Çeviriler üzerinde çalışmak için aşağıdaki bağlantıyı ziyaret edebilirsiniz:

[Launchpad Çeviri Sayfası](https://translations.launchpad.net/linuxmint/latest/)

### Hata Bildirimi ve İyileştirme Önerileri

Mintinstall'da karşılaştığınız hataları bildirmek veya geliştirme önerilerinde bulunmak isterseniz, GitHub üzerindeki [sorun izleyici](https://github.com/linuxmint/mintinstall/issues) üzerinden geri bildirimde bulunabilirsiniz.

## Katkıda Bulunanlar

Bu proje, Linux Mint topluluğunun katkılarıyla geliştirilmiştir. Kodlama, hata raporlama, çeviri veya dokümantasyon ile katkıda bulunan tüm gönüllülere teşekkür ederiz.

## Lisans

Bu proje, [GNU Genel Kamu Lisansı](https://www.gnu.org/licenses/gpl-3.0.html) (GPLv3) ile lisanslanmıştır. Daha fazla bilgi için lütfen lisans belgesine göz atın.
