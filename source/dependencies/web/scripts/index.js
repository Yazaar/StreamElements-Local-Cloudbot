document.querySelector('script').innerHTML = ''

document.getElementById('server_port-input').value = SetupValues.server_port
document.getElementById('exec_per_second-input').value = SetupValues.executions_per_second
document.getElementById('jwt-input').value = SetupValues.jwt_token
document.getElementById('user_id-input').value = SetupValues.user_id
document.getElementById('tmi-input').value = SetupValues.tmi
document.getElementById('tmi_username-input').value = SetupValues.tmi_twitch_username
document.getElementById('twitch_channel-input').value = SetupValues.twitch_channel
document.getElementById('use_node-input').checked = SetupValues.use_node

function createExtentions(data) {
    let temp = ''
    for (let i of data) {
        if (i.state === true) {
            temp += '<section class="ExtensionItem"><input type="checkbox" checked><p>' + i.module + '</p></section>'
        } else {
            temp += '<section class="ExtensionItem"><input type="checkbox"><p>' + i.module + '</p></section>'
        }
    }
    document.querySelector('article#extensions section.data').innerHTML = temp

    for (let i of document.querySelectorAll('section.ExtensionItem input[type="checkbox"]')) {
        i.addEventListener("change", (e) => {
            if (Waiting4Response === true) {
                ToggleQueue.push({
                    "item": e.target.parentNode.querySelector("p").innerHTML,
                    "to": e.target.checked
                })
            } else {
                Waiting4Response = true
                s.emit("toggle", {
                    "item": e.target.parentNode.querySelector("p").innerHTML,
                    "to": e.target.checked
                })
            }
        })
    }
}

function createLog(title, message) {
    return '<div>' + '<h2>' + title + '</h2>' + '<p>' + message + '</p>' + '</div>'
}

let s = io.connect(window.location.origin)
let Waiting4Response = false
let ToggleQueue = []
let ReloadStatus = false
let Waiting4Save = false

document.getElementById('ResetExtensions').addEventListener('click', () => {
    if (ReloadStatus === false){
        ReloadStatus = true
        s.emit('ReloadExtensions')
    }
})

for (let i of document.querySelectorAll('article#setup section.data section div')){
    i.addEventListener('click', () => {
        let node = i.parentNode.querySelector('input')

        if (node.id == 'server_port-input'){
            if (Waiting4Save === false){
                for (let j of document.querySelectorAll('article#setup section.data section div')){
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {'server_port':parseInt(node.value)})
            }
        }else if (node.id == 'exec_per_second-input'){
            if (Waiting4Save === false){
                for (let j of document.querySelectorAll('article#setup section.data section div')){
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {'executions_per_second':parseFloat(node.value)})
            }
        }else if (node.id == 'jwt-input'){
            if (Waiting4Save === false){
                for (let j of document.querySelectorAll('article#setup section.data section div')){
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {'jwt_token':node.value})
            }
        }else if (node.id == 'user_id-input'){
            if (Waiting4Save === false){
                for (let j of document.querySelectorAll('article#setup section.data section div')){
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {'user_id':node.value})
            }
        }else if (node.id == 'tmi-input'){
            if (Waiting4Save === false){
                for (let j of document.querySelectorAll('article#setup section.data section div')){
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {'tmi':node.value})
            }
        }else if (node.id == 'tmi_username-input'){
            if (Waiting4Save === false){
                for (let j of document.querySelectorAll('article#setup section.data section div')){
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {'twitch_channel':node.value})
            }
        }else if (node.id == 'twitch_channel-input'){
            if (Waiting4Save === false){
                for (let j of document.querySelectorAll('article#setup section.data section div')){
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {'tmi_twitch_username':node.value})
            }
        }
    })
}

document.getElementById('use_node-input').addEventListener('change', () => {
    if (Waiting4Save === true){
        if (document.getElementById('use_node-input').checked === true){
            document.getElementById('use_node-input').checked == false
        } else {
            document.getElementById('use_node-input').checked == true
        }
        return
    }
    Waiting4Save = true
    for (let j of document.querySelectorAll('article#setup section.data section div')){
        j.style.background = '#ff0000'
    }
    s.emit('UpdateSettings', {'use_node':document.getElementById('use_node-input').checked})
})

document.getElementById('ClearEvents').addEventListener('click', () => {
    document.querySelector('article#events section.data').innerHTML = ''
})
document.getElementById('ClearLogs').addEventListener('click', () => {
    document.querySelector('article#logs section.data').innerHTML = ''
    s.emit('ClearLogs')
})
document.getElementById('ClearMessages').addEventListener('click', () => {
    document.querySelector('article#messages section.data').innerHTML = ''
})


s.on('UpdatedSettings', () => {
    for (let j of document.querySelectorAll('article#setup section.data section div')){
        j.style.background = ''
    }
    Waiting4Save = false
})

s.on('ReloadChange', (message) => {
    createExtentions(message.data)
    ReloadStatus = false
})

s.on("message", (message) => {
    console.log(message)
})

s.on('log', (message) => {
    document.querySelector('article#logs section.data').innerHTML += createLog(message.module, message.message)
    for (let i of document.querySelectorAll('section.ExtensionItem p')) {
        if (i.innerHTML === message.module) {
            if (i.parentNode.querySelector('input').checked) {
                i.parentNode.querySelector('input').click()
            }
        }
    }
})

s.on('StreamElementsEvent', (data) => {
    if (!data.listener.includes('latest')){
        return
    }
    if (document.querySelector('article#events section.data').childElementCount > 99){
        document.querySelector('article#events section.data').removeChild(document.querySelector('article#events section.data').firstElementChild)
    }
    document.querySelector('article#events section.data').innerHTML += '<p>' + data.event.type + ' => ' + data.event.name + '</p>'
})

s.on('StreamElementsTestEvent', (data) => {
    if (!data.listener.includes('latest')){
        return
    }
    if (document.querySelector('article#events section.data').childElementCount > 99){
        document.querySelector('article#events section.data').removeChild(document.querySelector('article#events section.data').firstElementChild)
    }
    document.querySelector('article#events section.data').innerHTML += '<p>' + data.event.type + ' => ' + data.event.name + '</p>'
})

s.on("toggle", (message) => {
    if (ToggleQueue.length == 0) {
        Waiting4Response = false
    } else {
        s.emit("toggle", ToggleQueue[0])
        ToggleQueue.shift()
    }
})

s.on('TwitchMessage', (message) => {
    if (document.querySelector('article#messages section.data').childElementCount > 99){
        document.querySelector('article#messages section.data').removeChild(document.querySelector('article#messages section.data').firstElementChild)
    }
    document.querySelector('article#messages section.data').innerHTML += '<p>' + message.name + ': ' + message.message + '</p>'
})

createExtentions(data)

for (let i of logs) {
    document.querySelector('article#logs section.data').innerHTML += createLog(i.module, i.message)
}