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
    let new_element = document.createElement('div')
    let new_h2 = document.createElement('h2')
    let new_p = document.createElement('p')
    new_h2.innerText = title
    new_p.innerText = message
    new_element.appendChild(new_h2)
    new_element.appendChild(new_p)
    return new_element
}

function createSettings(json_object) {
    let items
    try {
        items = Object.keys(json_object.settings)
    } catch (error) {
        return
    }
    let new_element = document.createElement('div')
    let new_button = document.createElement('div')
    new_button.innerText = json_object.name
    new_button.classList.add('OpenCloseButton')
    new_button.addEventListener('click', (e) => {
        if (e.target.parentNode.querySelector('section').style.display === 'block') {
            e.target.parentNode.querySelector('section').style.display = 'none'
        } else {
            e.target.parentNode.querySelector('section').style.display = 'block'
        }
    })
    new_element.appendChild(new_button)
    let new_settings = document.createElement('section')
    new_settings.style.display = 'none'
    new_settings.setAttribute('data-path', json_object.path)
    new_settings.setAttribute('data-name', json_object.name)
    for (let i of items) {
        let setting = document.createElement('section')
        let title = document.createElement('h3')
        title.innerText = i
        setting.appendChild(title)
        let input = document.createElement('input')
        let sub_settings
        input.name = i
        try {
            sub_settings = Object.keys(json_object.settings[i])
        } catch (error) {
            sub_settings = []
        }
        for (let j of sub_settings) {
            if (j === 'tip') {
                let input_tip = document.createElement('p')
                input_tip.innerText = json_object.settings[i][j]
                setting.appendChild(input_tip)
            } else {
                input[j] = json_object.settings[i][j]
                if (j.toLowerCase() === 'type' && json_object.settings[i][j].toLowerCase() === 'range') {
                    let current_value = document.createElement('p')
                    current_value.classList.add('current_value')
                    setting.appendChild(current_value)
                    input.addEventListener('input', (e) => {
                        e.target.parentNode.querySelector('p.current_value').innerText = '(' + e.target.value + ')'
                    })
                    input.addEventListener('change', (e) => {
                        e.target.parentNode.querySelector('p.current_value').innerText = '(' + e.target.value + ')'
                    })
                } else if (j.toLowerCase() === 'type' && json_object.settings[i][j].toLowerCase() === 'number'){
                    input.addEventListener('input', (e)=>{
                        if(e.target.max !== '' && parseFloat(e.target.value) > parseFloat(e.target.max)){
                            e.target.value = e.target.max
                        }
                        if(e.target.min !== '' && parseFloat(e.target.value) < parseFloat(e.target.min)){
                            e.target.value = e.target.min
                        }
                    })
                }
            }
        }
        if (json_object.current !== undefined && json_object.current[i] !== undefined) {
            input.value = json_object.current[i]
        }
        setting.appendChild(input)
        if(input.type.toLowerCase() === 'range'){
            setting.querySelector('p.current_value').innerText = '(' + setting.querySelector('input').value + ')'
        }
        new_settings.appendChild(setting)
    }
    let new_save = document.createElement('div')
    new_save.innerText = 'Save settings'
    new_save.classList.add('save_settings')
    new_save.addEventListener('click', (e)=>{
        let current_settings = {'path':e.target.parentNode.getAttribute('data-path'), 'name':e.target.parentNode.getAttribute('data-name'), 'settings':{}}
        let settings_nodes = e.target.parentNode.querySelectorAll('input')
        for (let i of settings_nodes){
            if (i.type.toLowerCase() === 'number' || i.type.toLowerCase() === 'range'){
                current_settings.settings[i.name] = parseInt(i.value)
            } else if (i.type.toLowerCase() === 'checkbox') {
                current_settings.settings[i.name] = i.checked
            } else {
                current_settings.settings[i.name] = i.value
            }
        }
        if(ExtensionSettings[current_settings.name].scripts !== undefined){
            current_settings.scripts = ExtensionSettings[current_settings.name].scripts
        }
        if(ExtensionSettings[current_settings.name].event !== undefined){
            current_settings.event = ExtensionSettings[current_settings.name].event
        }
        s.emit('ScriptSettings', current_settings)
    })
    new_settings.appendChild(new_save)
    new_element.appendChild(new_settings)
    document.querySelector('#settings section.data').appendChild(new_element)
}

let s = io.connect(window.location.origin)
let Waiting4Response = false
let ToggleQueue = []
let ReloadStatus = false
let Waiting4Save = false

let ExtensionSettings_keys = Object.keys(ExtensionSettings)

for (let extension of ExtensionSettings_keys) {
    createSettings(ExtensionSettings[extension])
}

document.getElementById('ResetExtensions').addEventListener('click', () => {
    if (ReloadStatus === false) {
        ReloadStatus = true
        s.emit('ReloadExtensions')
    }
})

for (let i of document.querySelectorAll('article#setup section.data section div')) {
    i.addEventListener('click', () => {
        let node = i.parentNode.querySelector('input')

        if (node.id == 'server_port-input') {
            if (Waiting4Save === false) {
                for (let j of document.querySelectorAll('article#setup section.data section div')) {
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {
                    'server_port': parseInt(node.value)
                })
            }
        } else if (node.id == 'exec_per_second-input') {
            if (Waiting4Save === false) {
                for (let j of document.querySelectorAll('article#setup section.data section div')) {
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {
                    'executions_per_second': parseFloat(node.value)
                })
            }
        } else if (node.id == 'jwt-input') {
            if (Waiting4Save === false) {
                for (let j of document.querySelectorAll('article#setup section.data section div')) {
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {
                    'jwt_token': node.value
                })
            }
        } else if (node.id == 'user_id-input') {
            if (Waiting4Save === false) {
                for (let j of document.querySelectorAll('article#setup section.data section div')) {
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {
                    'user_id': node.value
                })
            }
        } else if (node.id == 'tmi-input') {
            if (Waiting4Save === false) {
                for (let j of document.querySelectorAll('article#setup section.data section div')) {
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {
                    'tmi': node.value
                })
            }
        } else if (node.id == 'tmi_username-input') {
            if (Waiting4Save === false) {
                for (let j of document.querySelectorAll('article#setup section.data section div')) {
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {
                    'twitch_channel': node.value
                })
            }
        } else if (node.id == 'twitch_channel-input') {
            if (Waiting4Save === false) {
                for (let j of document.querySelectorAll('article#setup section.data section div')) {
                    j.style.background = '#ff0000'
                }
                Waiting4Save = true
                s.emit('UpdateSettings', {
                    'tmi_twitch_username': node.value
                })
            }
        }
    })
}

document.getElementById('use_node-input').addEventListener('change', () => {
    if (Waiting4Save === true) {
        if (document.getElementById('use_node-input').checked === true) {
            document.getElementById('use_node-input').checked == false
        } else {
            document.getElementById('use_node-input').checked == true
        }
        return
    }
    Waiting4Save = true
    for (let j of document.querySelectorAll('article#setup section.data section div')) {
        j.style.background = '#ff0000'
    }
    s.emit('UpdateSettings', {
        'use_node': document.getElementById('use_node-input').checked
    })
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
    for (let j of document.querySelectorAll('article#setup section.data section div')) {
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
    document.querySelector('article#logs section.data').appendChild(createLog(message.module, message.message))
    for (let i of document.querySelectorAll('section.ExtensionItem p')) {
        if (i.innerHTML === message.module) {
            if (i.parentNode.querySelector('input').checked) {
                i.parentNode.querySelector('input').click()
            }
        }
    }
})

s.on('StreamElementsEvent', (data) => {
    if (document.querySelector('article#events section.data').childElementCount > 99) {
        document.querySelector('article#events section.data').removeChild(document.querySelector('article#events section.data').firstElementChild)
    }
    let new_element = document.createElement('p')
    new_element.innerText = data.type + ' => ' + data.data.username
    document.querySelector('article#events section.data').appendChild(new_element)
})

s.on('StreamElementsTestEvent', (data) => {
    if (!data.listener.includes('latest')) {
        return
    }
    if (document.querySelector('article#events section.data').childElementCount > 99) {
        document.querySelector('article#events section.data').removeChild(document.querySelector('article#events section.data').firstElementChild)
    }
    let new_element = document.createElement('p')
    new_element.innerText = data.event.type + ' => ' + data.event.name
    document.querySelector('article#events section.data').appendChild(new_element)
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
    if (document.querySelector('article#messages section.data').childElementCount > 99) {
        document.querySelector('article#messages section.data').removeChild(document.querySelector('article#messages section.data').firstElementChild)
    }
    let new_element = document.createElement('p')
    new_element.innerText = message.name + ': ' + message.message
    document.querySelector('article#messages section.data').appendChild(new_element)
})

createExtentions(data)

for (let i of logs) {
    document.querySelector('article#logs section.data').appendChild(createLog(i.module, i.message))
}