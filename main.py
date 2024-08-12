from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.utils import platform
import mysql.connector
from decimal import Decimal
from tempfile import NamedTemporaryFile
import subprocess
import os

# MySQL bağlantısı için fonksiyon
def veritabani_baglanti():
    return mysql.connector.connect(
        host="94.73.144.133",
        user="u1773614_user894",
        password="HogwartsWaffle1845@",
        database="u1773614_db894"
    )

# Kategorilere göre ürünleri getiren fonksiyon
def urunleri_kategoriye_gore_getir(kategori):
    conn = veritabani_baglanti()
    cursor = conn.cursor()
    cursor.execute('SELECT id, ad, fiyat FROM urunler WHERE kategori = %s', (kategori,))
    urunler = cursor.fetchall()
    conn.close()
    return urunler

# Siparişleri veritabanına ekleyen fonksiyon
def siparis_ekle(masa_id, urun_id, miktar):
    conn = veritabani_baglanti()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO siparisler (masa_id, urun_id, miktar, tarih)
        VALUES (%s, %s, %s, NOW())
    ''', (masa_id, urun_id, miktar))
    conn.commit()
    conn.close()

# Önceki siparişleri veritabanına ekleyen fonksiyon
def onceki_siparis_ekle(masa_id, toplam_tutar):
    conn = veritabani_baglanti()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO onceki_siparisler (masa_id, toplam_tutar, tarih)
        VALUES (%s, %s, NOW())
    ''', (masa_id, toplam_tutar))
    conn.commit()
    conn.close()

# Masadaki siparişlerin toplam tutarını hesaplayan fonksiyon
def masa_toplam_tutar(masa_id):
    conn = veritabani_baglanti()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(siparisler.miktar * urunler.fiyat) 
        FROM siparisler 
        JOIN urunler ON siparisler.urun_id = urunler.id 
        WHERE siparisler.masa_id = %s
    ''', (masa_id,))
    toplam_tutar = cursor.fetchone()[0] or Decimal('0.00')
    conn.close()
    return toplam_tutar

# Siparişlerin detaylarını almak için fonksiyon
def masa_siparisleri_getir(masa_id):
    conn = veritabani_baglanti()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT urunler.kategori, urunler.ad, siparisler.miktar, urunler.fiyat 
        FROM siparisler 
        JOIN urunler ON siparisler.urun_id = urunler.id 
        WHERE siparisler.masa_id = %s
    ''', (masa_id,))
    siparisler = cursor.fetchall()
    conn.close()
    return siparisler

# Kivy uygulama sınıfı
class POSUygulama(App):
    def build(self):
        self.title = 'Hogwarts Waffle Cafe Adisyon Sistemi'
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Masa butonları
        self.masa_butonlari = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        self.urun_spinner = Spinner(text='Ürün Seçin', values=[], size_hint=(None, None), size=(200, 44))
        self.miktar_spinner = Spinner(text='Miktar Seçin', values=[str(i) for i in range(1, 11)], size_hint=(None, None), size=(200, 44))
        self.kategori_spinner = Spinner(text='Kategori Seçin', values=[], size_hint=(None, None), size=(200, 44))
        
        # Adisyon butonları
        btn_adisyon_yazdir = Button(text='Adisyon Yazdır', on_press=self.adisyon_yazdir, size_hint=(None, None), size=(200, 50))
        btn_masa_kapat = Button(text='Masa Kapat', on_press=self.masa_kapat, size_hint=(None, None), size=(200, 50))

        # Kategori, ürün ve miktar alanlarını içeren bir BoxLayout
        controls_layout = BoxLayout(orientation='vertical', spacing=10, size_hint=(1, None), height=300)
        controls_layout.add_widget(Label(text='Kategori:'))
        controls_layout.add_widget(self.kategori_spinner)
        controls_layout.add_widget(Label(text='Ürün:'))
        controls_layout.add_widget(self.urun_spinner)
        controls_layout.add_widget(Label(text='Miktar:'))
        controls_layout.add_widget(self.miktar_spinner)

        # Ana layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        main_layout.add_widget(Label(text='Masalar:'))
        main_layout.add_widget(self.masa_butonlari)
        main_layout.add_widget(controls_layout)
        main_layout.add_widget(Button(text='Sipariş Ekle', on_press=self.siparis_ekle, size_hint=(None, None), size=(200, 50)))
        main_layout.add_widget(btn_adisyon_yazdir)
        main_layout.add_widget(btn_masa_kapat)

        # Masalar ve butonları ekle
        self.masa_renkleri = {}
        self.masa_id = None

        masalar = self.masalari_getir()
        for masa_id, masa_adı in masalar:
            btn = Button(text=f'{masa_adı}', on_press=lambda btn, masa_id=masa_id: self.masa_sec(masa_id))
            self.masa_butonlari.add_widget(btn)
            self.masa_renkleri[masa_id] = btn

        self.update_kategori_spinner()
        
        return main_layout

    def masalari_getir(self):
        conn = veritabani_baglanti()
        cursor = conn.cursor()
        cursor.execute('SELECT id, isim FROM masalar')
        masalar = cursor.fetchall()
        conn.close()
        return masalar

    def update_kategori_spinner(self):
        conn = veritabani_baglanti()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT kategori FROM urunler')
        kategoriler = [row[0] for row in cursor.fetchall()]
        conn.close()
        self.kategori_spinner.values = ['Kategori Seçin'] + kategoriler
        self.kategori_spinner.bind(text=self.on_kategori_select)

    def on_kategori_select(self, spinner, text):
        if text != 'Kategori Seçin':
            self.update_urun_spinner(text)

    def update_urun_spinner(self, kategori):
        urunler = urunleri_kategoriye_gore_getir(kategori)
        self.urun_spinner.values = ['Ürün Seçin'] + [urun_adı for _, urun_adı, _ in urunler]
        self.urun_dict = {urun_adı: urun_id for urun_id, urun_adı, _ in urunler}

    def masa_sec(self, masa_id):
        self.masa_id = masa_id
        self.masa_renkleri[masa_id].background_color = (0, 1, 0, 1)  # Yeşil renk
        self._show_popup('Masa Seçildi', f'Masa {masa_id} seçildi. Sipariş verebilirsiniz.')
        self.update_urun_spinner(self.kategori_spinner.text)

    def siparis_ekle(self, instance):
        if self.masa_id:
            urun_adı = self.urun_spinner.text
            miktar = self.miktar_spinner.text
            if urun_adı != 'Ürün Seçin' and miktar != 'Miktar Seçin':
                try:
                    miktar = int(miktar)
                    urun_id = self.urun_dict.get(urun_adı)
                    if urun_id:
                        siparis_ekle(self.masa_id, urun_id, miktar)
                        self._show_popup('Başarılı', 'Sipariş başarıyla eklendi!')
                        self.urun_spinner.text = 'Ürün Seçin'
                        self.miktar_spinner.text = 'Miktar Seçin'
                    else:
                        self._show_popup('Hata', 'Ürün bulunamadı.')
                except ValueError:
                    self._show_popup('Hata', 'Miktar sayısal bir değer olmalıdır.')
            else:
                self._show_popup('Hata', 'Tüm alanlar doldurulmalıdır ve bir ürün seçilmelidir.')
        else:
            self._show_popup('Hata', 'Bir masa seçilmelidir.')

    def masa_kapat(self, instance):
        if self.masa_id:
            toplam_tutar = masa_toplam_tutar(self.masa_id)
            onceki_siparis_ekle(self.masa_id, toplam_tutar)
            self.masa_renkleri[self.masa_id].background_color = (1, 0, 0, 1)  # Kırmızı renk
            self._show_popup('Başarılı', 'Masa kapatıldı ve adisyon oluşturuldu.')
        else:
            self._show_popup('Hata', 'Bir masa seçilmelidir.')

    def adisyon_yazdir(self, instance):
        if self.masa_id:
            dosya_yolu = self.adisyon_olustur(self.masa_id)
            if dosya_yolu:
                try:
                    if platform == 'win':
                        subprocess.run(['notepad', '/p', dosya_yolu], check=True)
                    else:
                        subprocess.run(['lp', dosya_yolu], check=True)
                    self._show_popup('Başarılı', 'Adisyon yazdırma işlemi tamamlandı.')
                except Exception as e:
                    self._show_popup('Hata', f'Yazdırma sırasında bir hata oluştu: {str(e)}')
            else:
                self._show_popup('Hata', 'Adisyon yazılamadı.')
        else:
            self._show_popup('Hata', 'Bir masa seçilmelidir.')

    def adisyon_olustur(self, masa_id):
        siparisler = masa_siparisleri_getir(masa_id)
        
        if not siparisler:
            return None
        
        # Kategorilere göre siparişleri grupla
        kategoriler = {}
        toplam_tutar = Decimal('0.00')
        for kategori, urun_adı, miktar, birim_fiyat in siparisler:
            if kategori not in kategoriler:
                kategoriler[kategori] = []
            # Decimal dönüşümü yaparak işlemleri doğru yapın
            toplam_fiyat = Decimal(miktar) * Decimal(birim_fiyat)
            kategoriler[kategori].append((urun_adı, miktar, toplam_fiyat))
            toplam_tutar += toplam_fiyat

        # Adisyonu oluştur
        with NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt') as temp_file:
            temp_file.write("Hogwarts Waffle Cafe\n")
            temp_file.write("="*30 + "\n")

            for kategori, urunler in kategoriler.items():
                temp_file.write(f"{kategori}\n")
                for urun_adı, miktar, toplam_fiyat in urunler:
                    temp_file.write(f"  {urun_adı} x {miktar} = {toplam_fiyat:.2f} TL\n")
                temp_file.write("\n")

            temp_file.write("="*30 + "\n")
            temp_file.write(f"Toplam Tutar: {toplam_tutar:.2f} TL\n")
            temp_file.write("Afiyet Olsun\n")

            file_path = temp_file.name
        
        return file_path

    def _show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.3))
        popup.open()

# Uygulama başlatma
if __name__ == '__main__':
    POSUygulama().run()
