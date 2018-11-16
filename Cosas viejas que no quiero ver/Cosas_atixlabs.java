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

public Cuenta ( int tipo , long numeroCuenta , String titular ) {
this . tipo = tipo ;
this . numeroCuenta = numeroCuenta ;
this . titular = titular ;
this . descubiertoAcordado = 0 ;
saldo = 0 ;
}
  
public void depositar ( long monto ) {
saldo += monto ;
}
  
public void extraer ( long monto ) throws RuntimeException {
switch ( tipo ) {
  case CAJA_AHORRO : if ( monto > saldo )
    throw new RuntimeException ( "No hay dinero suficiente" );
  case CTA_CORRIENTE : if ( monto > saldo + descubiertoAcordado )
    throw new RuntimeException ( "No hay dinero suficiente" );
}
saldo -= monto ;
}
  }
