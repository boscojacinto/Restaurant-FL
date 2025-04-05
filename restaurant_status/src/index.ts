import * as Status from '@status-im/js';
//const Status = import('@status-im/js')

async function greet(name: string) {

    console.log(`Inside, greet`)
    console.log("peers:", Status.peers)
    
    //https://status.app/cc/G4kAAGRonYPjpc0PMM4IBWBIK9EhhLUiE4nkkhS4zoUezpC312ylKyDZ6y_HUHMygfoMrf7mdITSmxFU6Q-X41PU83_-nogfzRYKelpl6FAgs5pvlrKlANDcrO4QoBt92In40ULeKui2gsmqqanGWOdHw8mI1yaqztvyQONVbTIZGqrRtyQT#zQ3shUxKscXKPjihQphSByaDxbv3PPzCpMCuTGpKomMh96Pwm
    //https://status.app/cc/G4gAAGT-z_VGhZ-GEa2pA4-IAznHOHC4hkG2wQaVYdgYA8_o2Y2K_SEMfpbIBEiN3GSgiL-rq4lyned76a8fBdNZGmRuKIkYEk39MpqBBUC-TD8CETKMQ_GRxbhO2HhFGKh2E5SqY9mWGjq1qTa17YS2H9RBUwA=#zQ3shUxKscXKPjihQphSByaDxbv3PPzCpMCuTGpKomMh96Pwm
    //https://status.app/c/CxWACikKCEJsaW5rMTgyEhJPbmx5IEJsaW5rMTgyIGZhbnMYASIHI0ZFOEY1OQM=#zQ3shUxKscXKPjihQphSByaDxbv3PPzCpMCuTGpKomMh96Pwm
    try {
        const client = await Status.createClient({"publicKey": "CxWACikKCEJsaW5rMTgyEhJPbmx5IEJsaW5rMTgyIGZhbnMYASIHI0ZFOEY1OQM", "environment": "production"})
        console.log(`client, ${Object.keys(client)}`)
    }
    catch(e) {
        console.log("error:", e);
    }


    return `Hello, ${name}!`;
}

greet("World");

/*(()=>{
    await greet("World");   
});*/