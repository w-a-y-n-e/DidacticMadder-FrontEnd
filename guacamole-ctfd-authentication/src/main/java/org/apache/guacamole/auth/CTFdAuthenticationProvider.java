package org.apache.guacamole.auth;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.Cookie;
import org.apache.guacamole.GuacamoleException;
import org.apache.guacamole.net.auth.AbstractAuthenticationProvider;
import org.apache.guacamole.net.auth.Credentials;
import org.apache.guacamole.net.auth.credentials.CredentialsInfo;
import org.apache.guacamole.net.auth.UserContext;
import org.apache.guacamole.net.auth.AuthenticatedUser;
import org.apache.guacamole.net.auth.credentials.GuacamoleInvalidCredentialsException;
import org.apache.http.impl.client.BasicCookieStore;
import org.apache.http.impl.cookie.BasicClientCookie;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.conn.ssl.NoopHostnameVerifier;
import java.security.cert.CertificateException;
import java.security.NoSuchAlgorithmException;
import java.security.cert.X509Certificate;
import org.apache.http.conn.ssl.TrustStrategy;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.ssl.SSLContextBuilder;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.HttpClient;
import org.apache.http.util.EntityUtils;
import org.apache.http.HttpResponse;
import java.io.IOException;


/**
 * Authentication provider to use cookie from CTFd through custom CTFd plugin.
 * Used in conjunction with database authentication which stores connections.
 */
public class CTFdAuthenticationProvider extends AbstractAuthenticationProvider {

    @Override
    public String getIdentifier() {
        return "ctfd-authentication";
    }

    public AuthenticatedUser authenticateUser(Credentials credentials)
            throws GuacamoleException {
        // Pull HTTP header from request if present
        HttpServletRequest request = credentials.getRequest();
	if (request != null) {
	   Cookie[] cookies = request.getCookies();
	   String cookieName = "session";
           String cookieValue = "";
           String externalUsername = "";
           if (cookies != null) {
           for ( int i=0; i<cookies.length; i++) {
              Cookie cookie = cookies[i];
              if (cookieName.equals(cookie.getName()))
                 cookieValue = cookie.getValue();
            }
           }

                CTFdAuthenticatedUser authenticatedUser = new CTFdAuthenticatedUser();
                BasicCookieStore cookieStore = new BasicCookieStore();
                BasicClientCookie clientCookie = new BasicClientCookie("session", cookieValue);
                clientCookie.setDomain("127.0.0.1");
                clientCookie.setPath("/");
                cookieStore.addCookie(clientCookie);
		//HttpClient client = HttpClientBuilder.create().setDefaultCookieStore(cookieStore).build();
		try{
		HttpClient client = HttpClients.custom().setSSLContext(new SSLContextBuilder().loadTrustMaterial(null, new TrustStrategy() {
			    public boolean isTrusted(X509Certificate[] arg0, String arg1) throws CertificateException {
				            return true;
					        }
		}).build()).setSSLHostnameVerifier(NoopHostnameVerifier.INSTANCE).setDefaultCookieStore(cookieStore).build();
                
                        final HttpGet httpRequest = new HttpGet("https://127.0.0.1/getusername");
                        HttpResponse httpResponse = client.execute(httpRequest);
                        externalUsername=EntityUtils.toString(httpResponse.getEntity());
                    //assertThat(response.getStatusLine().getStatusCode(), equalTo(200));
                }
                catch (Exception e) {
                        e.printStackTrace();
                }
		//externalUsername="guacadmin";
                authenticatedUser.init(externalUsername, credentials);
                return authenticatedUser;
        }

        // Authentication not provided yet.
        throw new GuacamoleInvalidCredentialsException("Invalid login.", CredentialsInfo.USERNAME_PASSWORD);

    }
}
