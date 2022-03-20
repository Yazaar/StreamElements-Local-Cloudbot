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

function parseJSON(data) {
    try {
        parsed = JSON.parse(data)
    } catch(e) {
        parsed = null
    }
    return parsed
}

let s = io.connect(window.location.origin)
let Waiting4Response = false
let ToggleQueue = []
let Waiting4Save = false

let ResetExtensionBtnActive = false

let ResetExtensionBtn = document.querySelector('#ResetExtensions')
setTimeout(function() {
    ResetExtensionBtnActive = true
    ResetExtensionBtn.style.display = ''
}, 1000)

document.getElementById('ResetExtensions').addEventListener('click', () => {
    if (ResetExtensionBtnActive) {
        ResetExtensionBtn.style.display = 'none'
        ResetExtensionBtnActive = false
        s.emit('ResetExtensions')
    }
})

for (let i of document.querySelectorAll('article#setup .saveSetupButton')) {
    i.addEventListener('click', function() {
        if (Waiting4Save) {
            return
        }

        let e = document.querySelector('article#setup')
        if (e != null) {
            e.classList.add('WaitingForSave')
        }

        let obj = {}
        
        let node = this.parentNode.querySelector('input')

        switch (node.id) {
            case 'server_port-input':
                obj.server_port = parseInt(node.value)
                break
            case 'exec_per_second-input':
                obj.executions_per_second = parseFloat(node.value)
                break
            case 'jwt-input':
                obj.jwt_token =  node.value
                break
            case 'user_id-input':
                obj.user_id =  node.value
                break
            case 'tmi-input':
                obj.tmi =  node.value
                break
            case 'tmi_username-input':
                obj.tmi_twitch_username =  node.value
                break
            case 'twitch_channel-input':
                obj.twitch_channel =  node.value
                break
            default:
                return
        }

        s.emit('UpdateSettings', obj)
    })
}

let lastSEListenerMethod = document.querySelector('#SEListenerMethod').value
document.querySelector('#SEListenerMethod').addEventListener('input', function() {
    if (Waiting4Save) {
        this.value = lastSEListenerMethod
    }
    
    let val = parseInt(this.value)
    if (isNaN(val))
    {
        this.value = lastSEListenerMethod
        return
    }
    
    lastSEListenerMethod = this.value
    
    let e = document.querySelector('article#setup')
    if (e != null) {
        e.classList.add('WaitingForSave')
    }

    Waiting4Save = true

    s.emit('UpdateSettings', {
        SEListener: val
    })
})

for (let i of document.querySelectorAll('.OpenCloseButton')) {
    i.addEventListener('click', function() {
        document.querySelector(this.getAttribute('data-target')).classList.toggle('ClosedSetting')
    })
}

for (let i of document.querySelectorAll('.save_settings')) {
    i.addEventListener('click', function() {
        let name = this.getAttribute('data-name')
        let index = parseInt(this.getAttribute('data-index'))
        let settings = {}
        for (let j of this.parentElement.querySelectorAll('section input, section select')) {
            let value
            if (j.type.toLowerCase() === 'checkbox') {
                value = j.checked
            } else {
                value = j.value
            }
            if (/^\d+$/.test(value)) {
                value = parseInt(value)
            } else if (/^\d+\.\d+$/.test(value)) {
                value = parseFloat(value)
            }
            settings[j.getAttribute('data-settingname')] = value
        }
        s.emit('SaveSettings', {name: name, index: index, settings: settings})
    })
}

for (let i of document.querySelectorAll('.SetDefaultSetting')) {
    i.addEventListener('click', function() {
        let value = i.getAttribute('data-default')
        let input = i.parentElement.querySelector('input, select')
        
        if (input === null) {
            return
        }
        
        if (input.type.toLowerCase() === 'checkbox') {
            input.checked = value
        } else {
            input.value = value
        }
    })
}

for (let i of document.querySelectorAll('.ToggleExtension')) {
    i.addEventListener('click', function() {
        s.emit('ToggleExtension', {
            module: this.getAttribute('data-module'),
            active: this.checked
        })
    })
}

{
    let AddDeleteRegular = document.querySelector('#AddDeleteRegular')
    let RegularOperation = 0
    let RegularUser = ''
    document.getElementById('RegularInput').addEventListener('input', function() {
        RegularUser = this.value.toLowerCase()
        if (RegularUser === '') {
            AddDeleteRegular.innerText = 'Specify user'
            RegularOperation = 0
        } else if (this.parentElement.querySelector('option.RegularUser' + RegularUser) !== null) {
            AddDeleteRegular.innerText = 'Delete'
            RegularOperation = 1
        } else {
            AddDeleteRegular.innerText = 'Add'
            RegularOperation = 2
        }
    })

    document.getElementById('AddDeleteRegular').addEventListener('click', function() {
        switch (RegularOperation) {
            case 0:
                return
            case 1:
                s.emit('DeleteRegular', RegularUser)
                break
                case 2:
                s.emit('AddRegular', RegularUser)
                break
        }

        document.getElementById('RegularInput').value = ''
        RegularUser = ''
        RegularOperation = 0
        AddDeleteRegular.innerText = '-'
    })
}

document.getElementById('ClearEvents').addEventListener('click', () => {
    document.querySelector('article#events section.data').innerHTML = ''
    s.emit('ClearEvents')
})

document.getElementById('ClearLogs').addEventListener('click', () => {
    document.querySelector('article#logs section.data').innerHTML = ''
    s.emit('ClearLogs')
})

document.getElementById('ClearMessages').addEventListener('click', () => {
    document.querySelector('article#messages section.data').innerHTML = ''
    s.emit('ClearMessages')
})

let cooldownUntilTW = new Date()
let timeoutTW = false
let disableUpdateTwitchBtn = false
document.querySelector('#RestartTwitch').addEventListener('click', function() {
    if (disableUpdateTwitchBtn === true) {
        return
    }

    let currentTime = new Date()

    if (cooldownUntilTW > currentTime) {
        let duration = cooldownUntilTW - currentTime
        this.innerText = 'Restart: ' + parseInt((duration) / 1000) + 's cooldown'
        
        let e = this
        
        if (timeoutTW === false) {
            timeoutTW = setTimeout(function() {
                e.innerText = 'Restart'
                timeoutTW = false
            }, duration)
        }
        
        return
    }
    
    s.emit('RestartTwitch')
})

let cooldownUntilSE = new Date()
let timeoutSE = false
let disableUpdateSEBtn = false
document.querySelector('#RestartSE').addEventListener('click', function() {
    if (disableUpdateSEBtn === true) {
        return
    }

    let currentTime = new Date()

    if (cooldownUntilSE > currentTime) {
        let duration = cooldownUntilSE - currentTime
        this.innerText = 'Restart: ' + parseInt((duration) / 1000) + 's cooldown'
        
        let e = this
        
        if (timeoutSE === false) {
            timeoutSE = setTimeout(function() {
                e.innerText = 'Restart'
                timeoutSE = false
            }, duration)
        }
        
        return
    }
    
    s.emit('RestartSE')
})

s.on('RestartTwitch', function(data) {
    if (disableUpdateTwitchBtn) {
        return
    }
    let e = document.querySelector('#RestartTwitch')
    let duration
    if (data.state === -1) {
        cooldownUntil = new Date(data.cooldown * 1000)
        duration = cooldownUntil - new Date()
        e.innerText = 'Restart: ' + parseInt((duration) / 1000) + 's cooldown'
    } else if (data.state === 0) {
        duration = 1000
        disableUpdateTwitchBtn = true
        e.innerText = 'No new data'
    } else {
        duration = 1000
        disableUpdateTwitchBtn = true
        e.innerText = 'Restart complete'
    }
    if (timeoutTW === false) {
        timeoutTW = setTimeout(function() {
            e.innerText = 'Restart'
            timeoutTW = false
            disableUpdateTwitchBtn = false
        }, duration)
    }
})

s.on('RestartSE', function(data) {
    if (disableUpdateSEBtn) {
        return
    }
    let e = document.querySelector('#RestartSE')
    let duration
    if (data.state === -1) {
        cooldownUntil = new Date(data.cooldown * 1000)
        duration = cooldownUntil - new Date()
        e.innerText = 'Restart: ' + parseInt((duration) / 1000) + 's cooldown'
    } else if (data.state === 0) {
        duration = 1000
        disableUpdateSEBtn = true
        e.innerText = 'No new data'
    } else {
        duration = 1000
        disableUpdateSEBtn = true
        e.innerText = 'Restart complete'
    }
    if (timeoutSE === false) {
        timeoutSE = setTimeout(function() {
            e.innerText = 'Restart'
            timeoutSE = false
            disableUpdateSEBtn = false
        }, duration)
    }
})

s.on('AddRegular', function(name) {
    let e = document.createElement('option')
    e.value = name
    e.classList.add('RegularUser' + name)
    document.querySelector('#RegularList').appendChild(e)
})

s.on('DeleteRegular', function(name) {
    let e = document.querySelector('option.RegularUser' + name)
    if (e === null) {
        return
    }

    e.parentElement.removeChild(e)
})

s.on('UpdateSettings', () => {
    let e = document.querySelector('article#setup')
    if (e != null) {
        e.classList.remove('WaitingForSave')
    }
    
    Waiting4Save = false
})

s.on('ResetExtensions', (message) => {
    window.location.reload()
})

s.on("message", (message) => {
    console.log(message)
})

s.on('log', (message) => {
    document.querySelector('article#logs section.data').appendChild(createLog(message.module, message.message))
    for (let i of document.querySelectorAll('section.ExtensionItem p')) {
        if (i.innerHTML === message.module) {
            i.parentNode.querySelector('input').checked = false
        }
    }
})

s.on('StreamElementsEvent', (data) => {
    if (document.querySelector('article#events section.data').childElementCount > 99) {
        document.querySelector('article#events section.data').removeChild(document.querySelector('article#events section.data').lastChild)
    }
    
    let wrap = document.createElement('div')
    let h2 = document.createElement('h2')
    let p = document.createElement('p')

    h2.innerText = data.type

    switch (data.type) {
        case 'tip':
            p.innerText = data.data.amount + ' ' + data.data.currency + ' => ' + data.data.username
            break
        case 'cheer':
            p.innerText = data.data.amount + ' bits => ' + data.data.username
            break
        case 'host':
            p.innerText = data.data.amount + ' host => ' + data.data.username
            break
        case 'raid':
            p.innerText = data.data.amount + ' raid => ' + data.data.username
            break/*
        case 'perk':
            p.innerText = event.item + ' => ' + data.data.username
            break
        case 'merch':
            p.innerText = 'test merchname => ' + data.data.username
            break*/
        case 'subscriber':
            switch (data.data.tier) {
                case 'prime':
                    p.innerText = 'prime'
                    break
                case '2000':
                    p.innerText = 'tier 2'
                    break
                case '3000':
                    p.innerText = 'tier 3'
                    break
                default:
                    p.innerText = 'tier 1'
                    break
            }
            /*if (event.bulkGifted) {
                p.innerText += ' community gift => ' + event.sender + ' x' + event.amount
            } else */if (data.data.gifted) {
                p.innerText += ' gift => ' + data.data.sender + ' to ' + data.data.username
            } else {
                p.innerText += ', ' + data.data.amount + ' months => ' + data.data.username
            }
            break
        default:
            p.innerText = data.data.username
            break
    }
    

    wrap.appendChild(h2)
    wrap.appendChild(p)
    
    let e = document.querySelector('article#events section.data')
    e.insertBefore(wrap, e.firstChild)
})

s.on('StreamElementsTestEvent', (data) => {
    if (!data.listener.includes('latest')) {
        return
    }

    if (document.querySelector('article#events section.data').childElementCount > 99) {
        document.querySelector('article#events section.data').removeChild(document.querySelector('article#events section.data').lastChild)
    }

    let wrap = document.createElement('div')
    let h2 = document.createElement('h2')
    let p = document.createElement('p')

    let event = data.event

    if (event.type === 'perk') {
        h2.innerText = 'item redemption'
    } else {
        h2.innerText = event.type
    }

    if (event.isTest) {
        h2.innerText += ' (test)'
    }

    switch (event.type) {
        case 'follower':
            p.innerText = event.name
            break
        case 'tip':
            p.innerText = event.amount + ' TC => ' + event.name
            break
        case 'cheer':
            p.innerText = event.amount + ' bits => ' + event.name
            break
        case 'host':
            p.innerText = event.amount + ' viwers => ' + event.name
            break
        case 'raid':
            p.innerText = event.amount + ' viwers => ' + event.name
            break
        case 'perk':
            p.innerText = event.item + ' => ' + event.name
            break
        case 'merch':
            p.innerText = 'test merchname => ' + event.name
            break
        case 'subscriber':
            switch (event.tier) {
                case 'prime':
                    p.innerText = 'prime'
                    break
                case '2000':
                    p.innerText = 'tier 2'
                    break
                case '3000':
                    p.innerText = 'tier 3'
                    break
                default:
                    p.innerText = 'tier 1'
                    break
            }
            if (event.bulkGifted) {
                p.innerText += ' community gift => ' + event.sender + ' x' + event.amount
            } else if (event.gifted) {
                p.innerText += ' gift => ' + event.sender + ' to ' + event.name
            } else {
                p.innerText += ', ' + event.amount + ' months => ' + event.name
            }
            break
    }

    wrap.appendChild(h2)
    wrap.appendChild(p)

    let e = document.querySelector('article#events section.data')
    e.insertBefore(wrap, e.firstChild)
})

s.on('ToggleExtension', (message) => {
    data = parseJSON(message)

    if (data === null) { return }
    if (data.success === false) {
        for (let i of document.querySelectorAll('.ToggleExtension')) {
            if (i.getAttribute('data-module') === data.module) {
                i.checked = message.active
            }
        }
    }
})

s.on('TwitchMessage', (message) => {
    if (document.querySelector('article#messages section.data').childElementCount > 99) {
        document.querySelector('article#messages section.data').removeChild(document.querySelector('article#messages section.data').firstElementChild)
    }
    let new_element = document.createElement('p')
    new_element.innerText = message.name + ': ' + message.message
    new_element.classList.add('message')
    document.querySelector('article#messages section.data').appendChild(new_element)
})
