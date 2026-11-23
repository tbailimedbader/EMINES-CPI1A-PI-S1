#include <digitalWriteFast.h>
#include <FlexiTimer2.h>

// Définition des broches du codeur incrémental
#define codeurPinA 2
#define codeurPinB 3

// Définition des broches de commande du moteur
#define pinPwm 5
#define pinDir 7

// Rapport de réduction : nombre de tours moteur pour un tour de l'arbre de sortie
const float reduction = 30.0;

// Nombre de ticks comptés pour un tour du codeur
const int TICKS_PAR_TOUR_CODEUR = 64;

// Variables de mesure
float omega = 0;         // Vitesse angulaire en rad/s
float position = 0;      // Position angulaire en rad

// Commande de vitesse du moteur (PWM entre -255 et 255)
int pwmValeur = 0;       // Initialement arrêté (0)

// Variables pour la machine à états de la communication série
enum SerialState { WAITING_PWM, WAITING_DIR };
SerialState serialState = WAITING_PWM;
int saisiPwm = 0;

// Compteur des impulsions du codeur
volatile long ticksCodeur = 0;

// Période de mesure en millisecondes
#define delta_time_ms 50
const float delta_time_s = delta_time_ms / 1000.0;

// Drapeau indiquant qu'une nouvelle mesure est nécessaire
volatile bool mesureDemandee = false;

// --- PROTOTYPES DES FONCTIONS ---
void declencherMesure();
void GestionInterruptionCodeurPinA();
void GestionInterruptionCodeurPinB();
void commandeVitesse(int pwm_mot);

void setup() {
  // Initialisation de la communication série
  Serial.begin(9600);

  // Configuration des broches du moteur en sortie
  pinMode(pinPwm, OUTPUT);
  pinMode(pinDir, OUTPUT);

  // Configuration des broches du codeur en entrée
  pinMode(codeurPinA, INPUT);
  pinMode(codeurPinB, INPUT);

  // Activation des interruptions sur les deux voies du codeur
  attachInterrupt(digitalPinToInterrupt(codeurPinA), GestionInterruptionCodeurPinA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(codeurPinB), GestionInterruptionCodeurPinB, CHANGE);

  // Configuration du timer pour déclencher une mesure toutes les 50 ms
  FlexiTimer2::set(delta_time_ms, declencherMesure);
  FlexiTimer2::start();

  // Affichage du menu initial
  Serial.println("=========================================");
  Serial.println("   CONTROLE MOTEUR - CODEUR INCREMENTAL  ");
  Serial.println("=========================================");
  Serial.println("Entrer la valeur du PWM (entre 0 et 255) :");
}

void loop() {
  // Gestion de la saisie série pas à pas (non bloquante)
  if (Serial.available() > 0) {
    if (serialState == WAITING_PWM) {
      saisiPwm = Serial.parseInt();
      saisiPwm = constrain(saisiPwm, 0, 255);
      
      // Vider le buffer série
      while (Serial.available() > 0) Serial.read();

      Serial.print("-> PWM choisi : ");
      Serial.println(saisiPwm);
      Serial.println("Entrer le sens de rotation (1 pour Horaire, 0 pour Anti-horaire) :");
      serialState = WAITING_DIR;
    }
    else if (serialState == WAITING_DIR) {
      int sens = Serial.parseInt();
      
      // Vider le buffer série
      while (Serial.available() > 0) Serial.read();

      // Appliquer le sens (1 = positif/Horaire, 0 = négatif/Anti-horaire)
      if (sens == 0) {
        pwmValeur = -saisiPwm;
      } else {
        pwmValeur = saisiPwm;
      }

      Serial.print("-> Moteur en marche ! PWM = ");
      Serial.print(saisiPwm);
      if (pwmValeur >= 0) {
        Serial.println(" | Sens : Horaire (Clockwise)");
      } else {
        Serial.println(" | Sens : Anti-horaire (Counter-Clockwise)");
      }
      Serial.println("-----------------------------------------");
      Serial.println("Pour changer, entrer une nouvelle valeur PWM (0-255) :");
      
      serialState = WAITING_PWM;
    }
  }

  // Application de la commande au moteur en continu
  commandeVitesse(pwmValeur);

  // Lecture sécurisée du compteur de ticks
  noInterrupts();
  bool calculer = mesureDemandee;
  long deltaTicks = 0;

  if (calculer) {
    mesureDemandee = false;
    deltaTicks = ticksCodeur;
    ticksCodeur = 0;
  }
  interrupts();

  // Calcul et affichage de la vitesse et de la position toutes les 50 ms
  if (calculer && pwmValeur != 0) {
    // Calcul de la vitesse angulaire en rad/s
    omega = (deltaTicks * 2.0 * PI) / (TICKS_PAR_TOUR_CODEUR * reduction * delta_time_s);

    // Calcul de la position angulaire en rad
    position += (deltaTicks * 2.0 * PI) / (TICKS_PAR_TOUR_CODEUR * reduction);

    // Affichage des résultats avec indication du sens
    Serial.print("Position : ");
    Serial.print(position, 2);
    Serial.print(" rad | Omega : ");
    Serial.print(omega, 2);
    Serial.print(" rad/s | Sens : ");
    if (pwmValeur >= 0) {
      Serial.println("Horaire");
    } else {
      Serial.println("Anti-horaire");
    }
  }
}

// Fonction de réglage de la vitesse et du sens du moteur
void commandeVitesse(int pwm_mot) {
  pwm_mot = constrain(pwm_mot, -255, 255);

  if (pwm_mot >= 0) {
    analogWrite(pinPwm, pwm_mot);
    digitalWrite(pinDir, HIGH); // Sens Horaire
  } else {
    analogWrite(pinPwm, abs(pwm_mot));
    digitalWrite(pinDir, LOW);  // Sens Anti-horaire
  }
}

// Interruption associée à la voie A du codeur
void GestionInterruptionCodeurPinA() {
  if (digitalReadFast2(codeurPinA) == digitalReadFast2(codeurPinB)) {
    ticksCodeur++;
  } else {
    ticksCodeur--;
  }
}

// Interruption associée à la voie B du codeur
void GestionInterruptionCodeurPinB() {
  if (digitalReadFast2(codeurPinA) == digitalReadFast2(codeurPinB)) {
    ticksCodeur--;
  } else {
    ticksCodeur++;
  }
}

// Fonction appelée périodiquement par FlexiTimer2
void declencherMesure() {
  mesureDemandee = true;
}
