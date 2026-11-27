1 # define PWM_pin 3 // Broche PWM pour contr ôler la vitesse du moteur
2 # define DIR_pin 7 // Broche pour contr ôler le sens de rotation du
3 moteur
4
5 // Initialisation des variables
6 int pwm_valeur = 0; // Vitesse initiale du moteur ( entre 0 et 255)
7 int dir_valeur = 1; // Sens initial : 1 = sens direct , -1 = sens
inverse
8
9 void setup () {
10
11 // Initialisation de la communication série à 9600 bauds
12 Serial . begin (9600) ;
13
14 // Configuration des broches en sortie
15 pinMode ( PWM_pin , OUTPUT ) ;
16 pinMode ( DIR_pin , OUTPUT ) ;
17 }
18
19 void loop () {
20
21 // Vé rifie si des donn ées sont disponibles sur le port série
22 if ( Serial . available () ) {
23
24 // Lit le caract ère envoy é depuis le moniteur série
25 char command = Serial . read () ;
26
27 // Si la commande reçue est ’p ’, on modifie la vitesse du moteur
28 if ( command == ’p ’) {
29
30 // Lit la valeur num é rique envoy ée après la commande ’p’
31 pwm_valeur = Serial . parseFloat () ;
32
33 // Limite la vitesse maximale à 255
34 if ( pwm_valeur > 255) {
35 pwm_valeur = 255;
36 }
37
38 // Emp êche d’avoir une valeur de vitesse né gative
9
3.3 Mesure de la position et de la vitesse
39 else if ( pwm_valeur < 0) {
40 pwm_valeur = 0;
41 }
42 }
43
44 // Si la commande reçue est ’d ’, on modifie le sens de rotation
45 else if ( command == ’d ’) {
46
47 // Lit la valeur du sens de rotation
48 dir_valeur = Serial . parseFloat () ;
49
50 // Vé rifie que la valeur est bien é gale à 1 ou -1
51 // Si la valeur est incorrecte , on choisit le sens direct par dé
faut
52 if ( dir_valeur != 1 && dir_valeur != -1) {
53 dir_valeur = 1;
54 }
55 }
56 }
57
58 // Commande la vitesse du moteur avec un signal PWM_pin
59 // La valeur doit être comprise entre 0 et 255
60 analogWrite ( PWM_pin , pwm_valeur ) ;
61
62 // Si dir_valeur vaut 1 , le moteur tourne dans le sens direct
63 if ( dir_valeur == 1) {
64 digitalWrite ( DIR_pin , HIGH ) ;
65 }
66
67 // Si dir_valeur vaut -1 , le moteur tourne dans le sens inverse
68 else if ( dir_valeur == -1) {
69 digitalWrite ( DIR_pin , LOW ) ;
70 }
71 }
