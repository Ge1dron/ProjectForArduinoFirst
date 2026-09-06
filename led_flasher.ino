#define BLOCK_SIZE 512 // Размер блока больше 255!

uint16_t buffer[BLOCK_SIZE];
// ВАЖНО: тип uint16_t вместо byte, чтобы уметь считать дальше 255
volatile uint16_t sample_count = 0; 

void setup() {
  Serial.begin(1000000); 
  
  // Настройка АЦП (Free Running, делитель 32)
  ADMUX = (1 << REFS0) | 0; 
  ADCSRA = (1 << ADEN)  | (1 << ADATE) | (1 << ADIE) | (1 << ADPS2) | (0 << ADPS1) | (1 << ADPS0); 
  ADCSRA |= (1 << ADSC);
  sei(); 
}

ISR(ADC_vect) {
  if (sample_count < BLOCK_SIZE) {
    buffer[sample_count] = ADC; 
    sample_count++;
  }
}

void loop() {
  // Ждем полного заполнения большого блока
  if (sample_count >= BLOCK_SIZE) {
    
    // Передаем весь буфер. 
    // buffer — указатель на начало массива
    // BLOCK_SIZE * 2 — точный размер в байтах (512 элементов * 2 байта = 1024 байта)
    Serial.write((uint8_t*)buffer, BLOCK_SIZE * 2);
    
    sample_count = 0; // Сброс счетчика
  }
}
