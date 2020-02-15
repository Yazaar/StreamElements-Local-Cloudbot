let statusVariables = {
    socket_is_running: false,
    loading_socket: false,
    data: {}
}

// socket variable
let s

function startSocket(){
    document.querySelector('p#StatusMessage').innerText = 'Connecting...'
    s = io('http://' + statusVariables.data.LSE_IP + ':' + statusVariables.data.LSE_Port, {transports: ['websocket']})

    s.on('connect', function(){
        console.log('Connected')
        document.querySelector('p#StatusMessage').innerText = 'Connected'
    })

    s.on('connect_error', function(){
        document.querySelector('p#StatusMessage').innerText = 'Host unreachable'
    })

    s.on('disconnect', function(){
        if (document.querySelector('p#StatusMessage').innerText !== 'Reset complete' || true){
            document.querySelector('p#StatusMessage').innerText = 'Closed'
        }
    })

    s.on('reconnect_attempt', () => {
        s.io.opts.transports = ['polling', 'websocket']
    })

    s.on('error', function(e){
        console.log(e)
    })
}

document.querySelector('div#connectBTN').addEventListener('click', function(){
    let IP = document.querySelector('input#IP').value
    let PORT = parseInt(document.querySelector('input#Port').value)
    if(IP === ''){
        document.querySelector('p#StatusMessage').innerText = 'Invalid HOST'
        return
    }
    if(isFinite(PORT) === false){
        document.querySelector('p#StatusMessage').innerText = 'Invalid PORT'
        return
    }
    chrome.storage.local.set({LSE_IP: IP, LSE_Port: PORT}, function() {})
})

document.querySelector('div#resetBTN').addEventListener('click', function(){
    chrome.storage.local.set({LSE_IP: 'undefined', LSE_Port: 'undefined'}, function() {})
    document.querySelector('p#StatusMessage').innerText = 'Reset complete'
})

chrome.storage.local.get(['LSE_IP', 'LSE_Port'], function (result) {
    for (let i in result) {
        statusVariables.data[i] = result[i]
    }
    if (statusVariables.data.LSE_IP !== undefined && statusVariables.data.LSE_Port !== undefined && statusVariables.data.LSE_IP !== 'undefined' && statusVariables.data.LSE_Port !== 'undefined') {
        startSocket()
    }
})

chrome.storage.onChanged.addListener(function (changes, namespace) {
    for (let i in changes) {
        statusVariables.data[i] = changes[i].newValue
    }
    if (statusVariables.data.LSE_IP !== undefined && statusVariables.data.LSE_Port !== undefined && statusVariables.data.LSE_IP !== 'undefined' && statusVariables.data.LSE_Port !== 'undefined' && statusVariables.loading_socket === false) {
        startSocket()
    } else if(statusVariables.Socket_Is_Running === true) {
        s.close()
    }
})