^FX ********************************************************^FS
^FX ** 17.07.03 - Ajout sigle R a coté du logo Sécurité   **^FS
^FX ** 17.11.03 - Ajout rubrique FN30 -> CONTROLE         **^FS
^FX ** 14.03.07 - Passage à la norme ETI9                 **^FS
^FX ** 17.04.08 - Déplacement code barre lot pour CML     **^FS
^FX ** 21.06.11 - Ajout sigle UR                          **^FS
^FX ********************************************************^FS

^XA^MCY^PR4,4^XZ  ^FX Vitesse d'impression 5,5 -> 4,4 ^FS

^FX ------- Définition du format ------- ^FS
^XA^DFUC^FS
^PW2000^FS

^FX ------------- MASQUE --------------- ^FS
    ^FX ---------- Cadres ---------- ^FS
        ^FX ---- HORIZONTALE --- ^FS
        ^FO883,58^GB4,2455,4^FS         ^FX ligne top ^FS
        ^FO805,58^GB4,2455,4^FS         ^FX ligne CDE RTGE ^FS
        ^FO645,58^GB4,2455,4^FS         ^FX ligne CDE PROD ^FS
        ^FO385,58^GB4,2455,4^FS         ^FX ligne N° ETQ ^FS
        ^FO31,58^GB4,2455,4^FS          ^FX ligne bottom ^FS
        ^FO114,1285^GB4,1225,4^FS      ^FX ligne COFOR ^FS
        ^FO200,1285^GB4,1225,4^FS      ^FX ligne LOT + IND MOTIF ^FS
        ^FO300,1285^GB4,1225,4^FS      ^FX ligne REF FRNS ^FS
        ^FO558,1520^GB4,388,4^FS       ^FX ligne PDs BRUT ^FS
        ^FO469,1520^GB4,388,4^FS       ^FX ligne DATE ^FS
        ^FX -------------------- ^FS
        
        ^FX ---- VERTICALE ----- ^FS
        ^FO31,58^GB853,4,4^FS        ^FX ligne de gauche ^FS
        ^FO31,2510^GB853,4,4^FS        ^FX ligne de droite ^FS
        ^FO31,1285^GB355,4,4^FS        ^FX séparateur du bas milieu ^FS
        ^FO300,1528^GB350,4,4^FS       ^FX séparateur NB & DESCP ^FS
        ^FO388,1905^GB260,4,4^FS       ^FX séparateur QTe & Pds + date ^FS
        ^FO645,1285^GB160,4,4^FS       ^FX séparateur CDE RTGE & PT DEST ^FS
        ^FO115,1875^GB88,4,4^FS        ^FX séparateur LOT & IND MODIF ^FS
        ^FO805,860^GB80,4,4^FS        ^FX séparateur DEST & PTDECH ^FS
        ^FO805,1569^GB80,4,4^FS       ^FX séparateur PTDECH & EXP ^FS

        ^FX -------------------- ^FS
    ^FX ---------------------------- ^FS

    ^FX ------- Texte masque ------- ^FS
        ^A0R,24,24^FO856,58                    ^FD DEST         ^FS
        ^A0R,24,24^FO856,860                  ^FD PTDECH       ^FS
        ^A0R,24,24^FO856,1569                 ^FD Exp          ^FS
    
        ^A0R,24,24^FO779,58                    ^FD CDE RTGE     ^FS
        ^A0R,24,24^FO779,1285                  ^FD PT DEST      ^FS

        ^A0R,24,24^FO619,58                    ^FD CDE          ^FS
        ^A0R,24,24^FO587,58                    ^FD PROD (P)     ^FS
    
        ^A0R,24,24^FO619,1528                 ^FD Pds Net      ^FS
        ^A0R,24,24^FO531,1528                 ^FD Pds BRUT     ^FS
        ^A0R,24,24^FO444,1528                 ^FD DATE         ^FS
        ^A0R,24,24^FO619,1915                 ^FD QTE (Q)      ^FS
    
        ^A0R,24,24^FO359,58                    ^FD Num ETQ (S)   ^FS
        
        ^A0R,24,24^FO359,1285                 ^FD Nb           ^FS
        ^A0R,24,24^FO359,1528                 ^FD DESCP        ^FS
        ^A0R,24,24^FO272,1285                 ^FD REF FRNS (30S)^FS
        ^A0R,24,24^FO172,1285                 ^FD LOT          ^FS
    
        ^A0R,24,24^FO172,1880                 ^FD IND          ^FS
        ^A0R,24,24^FO140,1880                 ^FD MODIF        ^FS
    
        ^A0R,24,24^FO86,1285                  ^FD COFOR (V)    ^FS
        ^A0R,32,32^FO37,2430                  ^FD ETI9    ^FS

    ^FX ---------------------------- ^FS

^FX ------------------------------------ ^FS

^FX ------------ Variable -------------- ^FS
    ^FX ------ Texte variable ------ ^FS

        ^A0R,64,64^FO795,110                  ^FN20^FS         ^FX DEST ^FS
        ^A0R,64,64^FO795,920                  ^FNPTDECH^FS     ^FX FNPTDECH ^FS
        
        ^A0R,64,64^FO795,920                  ^FN97^FS         ^FX Made in France ^FS
        
        
        ^A0R,64,64^FO795,1590                 ^FN40 ^FS        ^FX EXP ^FS
    
        ^A0R,148,75^FO620,75                  ^FN15 ^FS        ^FX CDE RTGE ^FS
        ^A0R,188,118^FO610,1180               ^FN18 ^FS        ^FX Gauche / Droite ^FS
        ^A0R,188,118^FO610,1400               ^FN99^FS         ^FX PT DEST - POINT DE DESTINATION ^FS
        
        ^A0R,188,100^FO457,195                ^FN1^FS          ^FX N PROD ^FS
        ^A0R,96,96^FO384,900                  ^FN14^FS         ^FX AQP ^FS

        ^A0R,188,120^FO400,1100                ^FN98^FS         ^FX UR ^FS

        ^A0R,64,64^FO560,1565                 ^FN24^FS         ^FX NET ^FS
        ^A0R,64,64^FO471,1565                 ^FN21^FS         ^FX BRUT ^FS

        ^A0R,72,72^FO377,1565                 ^FN12^FS         ^FX Date ^FS
        ^A0R,188,188^FO445,2050               ^FN3^FS          ^FX Quatité ^FS
    
        ^A0R,188,188^FO190,185                ^FN7^FS          ^FX N Etiq ^FS

        ^A0R,32,32^FO37,174                   ^FN16^FS

        ^A0R,64,64^FO295,1335                 ^FN22^FS         ^FX NB colis par palette ^FS
        ^A0R,72,58^FO290,1550                 ^FN9^FS          ^FX Désignation ^FS

        ^A0R,80,73^FO190,1295                 ^FN10^FS         ^FX Fournisseur ^FS

        ^A0R,64,45^FO107,1290                 ^FN13^FS         ^FX N Lot ^FS

        ^A0R,64,64^FO120,1960                 ^FN17^FS         ^FX IND MODIF ^FS
    
        ^A0R,64,64^FO25,1305                  ^FN5^FS          ^FX COFOR ^FS

        ^A0R,24,24^FO37,68                     ^FN80^FS        ^FX 3 derniers chiffres de l'UM^FS

    ^FX ---------------------------- ^FS

    ^FX --------- Code BAR --------- ^FS

        ^FX CBar QTE ^FS
        ^BY3,1.0^FO410,1945^BC R,72,N,Y,Y,N^FN4^FS

        ^FX CBar REF FRNS ^FS
        ^BY3,1.0^FO215,1820^BC R,64,N,Y,Y,N^FN11^FS

        ^FX CBar COFOR ^FS
        ^BY2.5,1.0^FO42,1724^BC R,64,N,Y,Y,N^FN6^FS
        
        ^FX CBar Produit ^FS
        ^BY3,1.0^FO394,185^BCR,100,N,Y,Y,N^FN2^FS

        ^FX CBar N° Etiq ^FS
        ^BY5,1.0^FO70,185^BC R,159,N,Y,Y,N^FN8^FS

        ^FX CBar N° lot ^FS
        ^BY3,1.0^FO122,1500^BC R,72,N,Y,Y,N^FN23^FS

    ^FX ---------------------------- ^FS
    
    ^FX **************************************** ^FS
    ^FX ** Logo Sï¿½uritï¿½                   ** ^FS
    ^FX **************************************** ^FS
    ^A0R,100,140^FO370,1440            ^FN91^FS   ^FX S=Sécurité          ^FS
    ^A0R,100,140^FO540,1445            ^FN90^FS   ^FX R=Règlementation    ^FS


    ^FO380,1190^XGR:SECU2.grf,1,1^FS

    ^FX ---------------------------- ^FS
^FX ------------------------------------ ^FS


^PQ1,0,1,Y
^XZ
