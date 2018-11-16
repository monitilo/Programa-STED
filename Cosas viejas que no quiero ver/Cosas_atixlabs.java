public class Cuenta {
public static final int CTA_CORRIENTE = 0 ;
public static final int CAJA_AHORRO = 1 ;
private int tipo ;
private long numeroCuenta ;
private String titular ;
private long saldo ;
private long descubiertoAcordado ;
public Cuenta ( int tipo , long nCuenta , String titular , long descAcordado ) {
this . tipo = tipo ;
this . numeroCuenta = nCuenta ;
this . titular = titular ;
if ( tipo == CTA_CORRIENTE )
this . descubiertoAcordado = descAcordado ;
else this . descubiertoAcordado = 0 ;
saldo = 0 ;
}
