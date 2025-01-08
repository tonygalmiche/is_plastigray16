^FX ********************************************************^FS
^FX ** 03/03/2021 Creation                                **^FS
^FX ********************************************************^FS


^XA
^CI28                 ^FX Encodage en UTF-8
^MCY
^PR4,4^XZ             ^FX Vitesse d'impression 5,5 -> 4,4 ^FS

^FX ** Définition du format *************************************************^FS
^XA^DFUC^FS
^PW2000^FS

^FX ** Informations de base sur le positionnement ***************************^FS
^FX Resolution : 300dpi  : 300pt/pouce => 300pt/2,54cm => 1mm = 11.9pt  ^FS
^FX Gauche       : 5mm   = 60pt      ^FS
^FX Bas          : 4mm   = 40pt      ^FS
^FX Lageur C40   : 206mm = 2460pt    ^FS
^FX Hauteur C40  : 42mm  = 480pt     ^FS

^FX ** Cadres ***************************************************************^FS

^FX ** HORIZONTALE ^FS
^FO520,60   ^GB4,2460,4^FS     ^FX ligne haut (40+480)  ^FS
^FO400,1310 ^GB4,1210,4^FS     ^FX ligne sous point de destination (360+40) ^FS
^FO280,60   ^GB4,2460,4^FS     ^FX ligne milieu (240+40) ^FS
^FO208,1310 ^GB4,792,4^FS      ^FX ligne sous lot (40+72+96) ^FS
^FO112,1310 ^GB4,1210,4^FS     ^FX ligne sous description (40+72) ^FS
^FO40 ,60   ^GB4,2460,4^FS     ^FX ligne bas ^FS

^FX ** VERTICALE ************************************************************^FS
^FO40,60    ^GB480,4,4^FS     ^FX ligne de gauche ^FS
^FO40,1310  ^GB480,4,4^FS     ^FX ligne milieu (1250+60) ^FS
^FO208,1754 ^GB72,4,4 ^FS     ^FX ligne gauche DATE (60+1250+444) ^FS
^FO112,2102 ^GB168,4,4^FS     ^FX ligne gauche QTE (60+1250+792) ^FS
^FO40,2520  ^GB480,4,4^FS     ^FX ligne de droite (2460+40) ^FS


^FX ** Texte masque *********************************************************^FS
^A0R,24,24    ^FO490,60        ^FD CODE            ^FS
^A0R,24,24    ^FO460,60        ^FD PROD (P)        ^FS
^A0R,24,24    ^FO250,60        ^FD N°ETI (S)       ^FS
^A0R,24,24    ^FO490,1310      ^FD DEST            ^FS
^A0R,24,24    ^FO370,1310      ^FD CODE            ^FS
^A0R,24,24    ^FO340,1310      ^FD ROUTAGE         ^FS
^A0R,24,24    ^FO250,1310      ^FD N°LOT           ^FS
^A0R,24,24    ^FO250,1754      ^FD DATE            ^FS
^A0R,24,24    ^FO250,2102      ^FD QTE (Q)         ^FS
^A0R,24,24    ^FO178,1310      ^FD DESCRIPTION     ^FS
^A0R,24,24    ^FO82,1310       ^FD CODE            ^FS
^A0R,24,24    ^FO52,1310       ^FD VENDEUR (V)     ^FS
^A0R,188,116  ^FO510,2015      ^FD C :             ^FS ^FX Tampon operateur  ^FS


^FX ** Variables ************************************************************^FS
^A0R,70,70    ^FO410,1350  ^FN20  ^FS  ^FX POINT DESTINATION                 ^FS
^A0R,120,65   ^FO270,1430  ^FN15  ^FS  ^FX CODE ROUTAGE                      ^FS
^A0R,140,140  ^FO375,180   ^FN1   ^FS  ^FX CODE PRODUIT (P)                  ^FS
^A0R,130,130  ^FO140,180   ^FN7   ^FS  ^FX N Etiq                            ^FS
^A0R,64,45    ^FO205,1390  ^FN13  ^FS  ^FX N Lot                             ^FS
^A0R,72,72    ^FO205,1830  ^FN12  ^FS  ^FX Date                              ^FS
^A0R,85,85    ^FO185,2200  ^FN3   ^FS  ^FX Quantité                          ^FS
^A0R,40,40    ^FO550,60    ^FN16  ^FS  ^FX Adresse en haut                   ^FS
^A0R,65,58    ^FO110,1320  ^FN9   ^FS  ^FX Description                       ^FS
^A0R,64,64    ^FO35,1470   ^FN5   ^FS  ^FX COFOR                             ^FS
^A0R,130,130  ^FO140,920   ^FN14  ^FS  ^FX AQP                               ^FS
^A0R,188,118  ^FO55,1220   ^FN18  ^FS  ^FX Gauche / Droite                   ^FS


^FX ** Code BAR *************************************************************^FS
^BY3,1.0    ^FO125,2130  ^BC R,72,N,Y,Y,N   ^FN4  ^FS  ^FX CBar QTE          ^FS
^BY5,1.0    ^FO60,180    ^BC R,100,N,Y,Y,N  ^FN8  ^FS  ^FX CBar N° Etiq      ^FS
^BY5,1.0    ^FO290,180   ^BC R,100,N,Y,Y,N  ^FN2  ^FS  ^FX CBar Produit      ^FS
^BY2.5,1.0  ^FO42,1800   ^BC R,64,N,Y,Y,N   ^FN6  ^FS  ^FX CBar COFOR        ^FS



^FX ** Logo SECU *********************************************************** ^FS
^A0R,100,140  ^FO270,1230            ^FN91^FS        ^FX S=Sécurité          ^FS
^A0R,100,140  ^FO410,1230            ^FN90^FS        ^FX R=Règlementation    ^FS
^FO270,990   ^XGR:SECU2.grf,1,1                                             ^FS

^PQ1,0,1,Y
^XZ
